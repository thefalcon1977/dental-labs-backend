"""Dynaconf settings configuration.

Priority order (highest to lowest):
1. OS Environment variables (with APP_ prefix)
2. .env file variables (with APP_ prefix)
3. settings.toml file
"""

from dynaconf import Dynaconf

from .validators import validators

settings = Dynaconf(
    envvar_prefix="APP",
    settings_files=[
        "config/settings/settings.toml",
    ],
    environments=True,
    env_switcher="ENV",
    load_dotenv=True,
    dotenv_path=".env",
    validators=validators,
)

__all__ = ["settings"]
