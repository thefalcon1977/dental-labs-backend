"""Shared utilities for CLI commands."""

import multiprocessing
from pathlib import Path
from typing import Any

from alembic.config import Config

from config.settings import settings


def calculate_workers() -> int:
    """Calculate optimal number of workers based on CPU count and settings.

    Returns:
        Number of workers to use.
    """
    cpu_count = multiprocessing.cpu_count()
    configured_workers = settings.uvicorn.WORKERS
    max_workers = settings.uvicorn.WORKERS_MAX

    # If workers is set to 1, use 1 (development mode)
    if configured_workers == 1:
        return 1

    # Calculate workers: min(configured, max_allowed, cpu_count * 2 + 1)
    # Formula: (2 * CPU cores) + 1 is a common pattern for async workers
    optimal_workers = min(
        configured_workers,
        max_workers,
        (cpu_count * 2) + 1,
    )

    return max(1, optimal_workers)


def get_alembic_config() -> Config:
    """Get Alembic configuration.

    Returns:
        Alembic Config instance.

    Raises:
        FileNotFoundError: If alembic.ini is not found.
    """
    alembic_ini = Path("alembic.ini")
    if not alembic_ini.exists():
        raise FileNotFoundError("alembic.ini not found. Please create it first.")

    alembic_cfg = Config(str(alembic_ini))

    # Set database URL from settings (use sync driver for Alembic)
    if settings.database.ENABLED:
        database_url = (
            f"postgresql://"  # Use sync driver for Alembic
            f"{settings.database.USER}:{settings.database.PASSWORD}@"
            f"{settings.database.HOST}:{settings.database.PORT}/"
            f"{settings.database.NAME}"
        )
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)

    return alembic_cfg


def format_config_value(value: Any, key: str = "") -> str:
    """Format configuration value for display, masking sensitive information.

    Args:
        value: Configuration value to format
        key: Configuration key name (used for masking sensitive fields)

    Returns:
        Formatted string representation of the value
    """
    sensitive_keywords = ["password", "secret", "key", "token", "credential"]
    if any(keyword in key.lower() for keyword in sensitive_keywords):
        if isinstance(value, str) and value:
            return "*" * min(len(value), 20)
        return "***"

    if isinstance(value, dict):
        # Format dict nicely with key-value pairs
        if not value:
            return "{}"
        # For complex dicts, show a summary
        if len(str(value)) > 80:
            items = list(value.items())[:3]
            summary = ", ".join(f"{k}={v}" for k, v in items)
            remaining = len(value) - 3
            if remaining > 0:
                return f"{summary} ... (+{remaining} more)"
            return summary
        # For smaller dicts, format nicely
        formatted_items = []
        for k, v in value.items():
            if isinstance(v, (str, int, float, bool, type(None))):
                formatted_items.append(f"{k}={v}")
            else:
                formatted_items.append(f"{k}=<{type(v).__name__}>")
        return ", ".join(formatted_items)

    if isinstance(value, list):
        if not value:
            return "[]"
        # Format list nicely
        if len(value) <= 5:
            return ", ".join(str(item) for item in value)
        return (
            f"{', '.join(str(item) for item in value[:5])} ... (+{len(value) - 5} more)"
        )

    if isinstance(value, bool):
        return str(value)

    if value is None:
        return "None"

    # Check if it's a non-serializable object
    if not isinstance(value, (str, int, float, bool, type(None))):
        # Try to get a string representation, but limit length
        str_repr = str(value)
        if len(str_repr) > 100:
            return f"<{type(value).__name__}>"
        if "<" in str_repr and "object" in str_repr.lower():
            return f"<{type(value).__name__}>"

    return str(value)


def _flatten_nested_dict(
    value: Any,
    parent_key: str,
    skip_patterns: list[str],
    max_depth: int = 5,
    current_depth: int = 0,
    visited: set[int] | None = None,
) -> dict[str, Any]:
    """Recursively flatten nested dictionaries and dict-like objects.

    Args:
        value: Value to flatten (dict, Box, or dict-like object)
        parent_key: Parent key prefix
        skip_patterns: Patterns to skip
        max_depth: Maximum recursion depth (reduced to 5 to prevent hangs)
        current_depth: Current recursion depth
        visited: Set of object IDs already visited (for circular reference detection)

    Returns:
        Flattened dictionary with dot-separated keys
    """
    if current_depth >= max_depth:
        return {}

    # Initialize visited set on first call
    if visited is None:
        visited = set()

    # Check for circular references using object ID
    value_id = id(value)
    if value_id in visited:
        return {}  # Circular reference detected, skip
    visited.add(value_id)

    result: dict[str, Any] = {}

    try:
        # Try to get items from dict-like object
        items: list[tuple[str, Any]] = []
        if isinstance(value, dict):
            items = list(value.items())
        elif hasattr(value, "__dict__"):
            # Get attributes from object
            try:
                items = [
                    (k, v)
                    for k, v in value.__dict__.items()
                    if not k.startswith("_") and not callable(v)
                ]
            except (AttributeError, TypeError, RecursionError):
                return {}
        elif hasattr(value, "items"):
            try:
                items = list(value.items())
            except (TypeError, ValueError, RecursionError):
                return {}
        else:
            return {}

        for key, val in items:
            # Skip if key matches skip patterns
            if any(pattern in str(key).upper() for pattern in skip_patterns):
                continue

            new_key = f"{parent_key}.{key}" if parent_key else key

            # Check if value is a nested dict-like object
            # Skip if it's a simple type or already visited
            is_nested_dict = (
                isinstance(val, dict)
                or (
                    hasattr(val, "__dict__")
                    and not isinstance(val, (str, int, float, bool, type(None)))
                    and id(val) not in visited
                )
                or (
                    hasattr(val, "items")
                    and not isinstance(val, (str, bytes, list))
                    and id(val) not in visited
                )
            )

            if is_nested_dict:
                # Recursively flatten nested dictionaries
                nested = _flatten_nested_dict(
                    val, new_key, skip_patterns, max_depth, current_depth + 1, visited
                )
                result.update(nested)
            else:
                # Simple value, add directly
                result[new_key] = val

    except (RecursionError, MemoryError, AttributeError, TypeError):
        # If we hit recursion or memory issues, return what we have
        return result
    finally:
        # Remove from visited set when done (to allow same object at different paths)
        visited.discard(value_id)

    return result


def get_all_settings() -> dict[str, Any]:
    """Get all settings from Dynaconf (from .env, settings.toml, and OS env vars).

    Uses Dynaconf's built-in as_dict() method to get all settings,
    then recursively flattens nested dictionaries.

    Returns:
        Dictionary of all user-relevant settings with nested keys as dot-separated strings
    """
    config_dict: dict[str, Any] = {}

    # Patterns to filter out (Dynaconf internals)
    skip_patterns = [
        "_FOR_DYNACONF",
        "DYNACONF_",
        "FOR_DYNACONF",
        "LOADED_BY_LOADERS",
        "LOADED_ENVS",
        "LOADED_NAMESPACES",
        "LOADERS",
        "STORE",
        "RENAMED_VARS",
        "SECRETS_FOR_DYNACONF",
        "VAULT_",
        "YAML_LOADER",
        "COMMENTJSON",
        "CORE_LOADERS",
        "DOTTED_LOOKUP",
        "NESTED_SEPARATOR",
        "ENVVAR_",
        "ENV_SWITCHER",
        "ENVIRONMENTS",
        "DEFAULT_ENV",
        "MAIN_ENV",
        "FORCE_ENV",
        "GLOBAL_ENV",
        "BASE_NAMESPACE",
        "NAMESPACE",
        "PROJECT_ROOT",
        "ROOT_PATH",
        "APPLY_DEFAULT",
        "VALIDATE_ON_UPDATE",
        "SYSENV_FALLBACK",
        "SILENT_ERRORS",
        "FRESH_VARS",
        "DOTENV_",
        "ENCODING",
        "AUTO_CAST",
        "MERGE_ENABLED",
        "LOWERCASE_READ",
        "INCLUDES",
        "PRELOAD",
        "SKIP_FILES",
        "INSTANCE",
        "FILTER_STRATEGY",
        "CONFIGURED",
        "CURRENT_ENV",
        "CURRENT_NAMESPACE",
        "SETTINGS_FILE",
        "SETTINGS_MODULE",
    ]

    try:
        # Use Dynaconf's as_dict() to get all settings (includes .env, env vars, settings.toml)
        # internal=False excludes Dynaconf internals
        all_settings = settings.as_dict(internal=False)

        # Recursively flatten nested dictionaries
        for key, value in all_settings.items():
            # Skip if key matches skip patterns
            if any(pattern in str(key).upper() for pattern in skip_patterns):
                continue

            # Skip callable values
            if callable(value):
                continue

            # Flatten nested dictionaries
            if isinstance(value, dict):
                try:
                    flattened = _flatten_nested_dict(value, key, skip_patterns)
                    if flattened:
                        config_dict.update(flattened)
                    else:
                        config_dict[key] = value
                except (RecursionError, MemoryError):
                    config_dict[key] = "<nested object (too deep)>"
            elif not isinstance(value, (str, int, float, bool, list, type(None))):
                # Try to flatten non-simple types
                try:
                    flattened = _flatten_nested_dict(value, key, skip_patterns)
                    if flattened:
                        config_dict.update(flattened)
                    else:
                        # If it's not a dict-like object, just convert to string
                        config_dict[key] = str(value)[:100]
                except (RecursionError, MemoryError, AttributeError, TypeError):
                    config_dict[key] = "<complex object>"
            else:
                # Simple value, add directly
                config_dict[key] = value

    except (AttributeError, TypeError, Exception):
        # Fallback: try to get settings manually if as_dict() fails
        try:
            # Get all attributes that don't start with underscore
            for attr_name in dir(settings):
                if attr_name.startswith("_"):
                    continue

                # Skip if matches skip patterns
                if any(pattern in attr_name.upper() for pattern in skip_patterns):
                    continue

                try:
                    attr_value = getattr(settings, attr_name)
                    if callable(attr_value):
                        continue

                    # Flatten if needed
                    if isinstance(attr_value, dict):
                        flattened = _flatten_nested_dict(
                            attr_value, attr_name, skip_patterns
                        )
                        if flattened:
                            config_dict.update(flattened)
                        else:
                            config_dict[attr_name] = attr_value
                    elif not isinstance(
                        attr_value, (str, int, float, bool, list, type(None))
                    ):
                        try:
                            flattened = _flatten_nested_dict(
                                attr_value, attr_name, skip_patterns
                            )
                            if flattened:
                                config_dict.update(flattened)
                        except (RecursionError, MemoryError, AttributeError, TypeError):
                            pass
                    else:
                        config_dict[attr_name] = attr_value
                except (AttributeError, TypeError):
                    continue
        except (RuntimeError, ValueError, KeyError):
            # Settings access failed - this is a fallback, so we can ignore errors
            # and return whatever we've collected so far
            pass

    return config_dict


def organize_config(config_dict: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Organize configuration into sections (top-level and nested).

    Args:
        config_dict: Dictionary with dot-separated keys for nested config

    Returns:
        Organized dictionary with sections as top-level keys
    """
    organized: dict[str, dict[str, Any]] = {}

    # Define section order and mapping
    section_order = [
        "application",
        "database",
        "redis",
        "keycloak",
        "uvicorn",
        "logging",
        "security",
        "cors",
    ]

    for key, value in config_dict.items():
        if "." in key:
            section, setting = key.split(".", 1)
            # Normalize section name
            section_lower = section.lower()
            if section_lower not in organized:
                organized[section_lower] = {}
            organized[section_lower][setting] = value
        else:
            if "application" not in organized:
                organized["application"] = {}
            organized["application"][key] = value

    # Sort sections by defined order, then alphabetically
    sorted_organized: dict[str, dict[str, Any]] = {}
    for section in section_order:
        if section in organized:
            sorted_organized[section] = organized.pop(section)

    # Add remaining sections alphabetically
    for section in sorted(organized.keys()):
        sorted_organized[section] = organized[section]

    return sorted_organized


def get_section_icon(section: str) -> str:
    """Get section name for configuration section (no icons, Typer style).

    Args:
        section: Configuration section name

    Returns:
        Section name string (no icons)
    """
    return ""
