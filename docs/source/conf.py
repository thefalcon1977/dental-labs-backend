# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import sys
from pathlib import Path

# Add project root to path to import version
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import version from single source of truth (pyproject.toml via apps.core.version)
# This ensures the documentation version matches the application version
try:
    from apps.core.version import __version__
except ImportError as e:
    # If import fails, try to read directly from pyproject.toml
    import tomllib

    pyproject_path = project_root / "pyproject.toml"
    if pyproject_path.exists():
        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
                __version__ = data.get("project", {}).get("version")
                if not __version__:
                    raise RuntimeError(
                        "Version not found in pyproject.toml [project] section. "
                        'Please ensure pyproject.toml contains: [project] version = "..."'
                    )
        except Exception as read_error:
            raise RuntimeError(
                f"Failed to read version from pyproject.toml: {read_error}. "
                f"Original import error: {e}"
            )
    else:
        raise RuntimeError(
            f"Could not find pyproject.toml at {pyproject_path}. "
            f"Original import error: {e}"
        )

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Microservices FastAPI Template"
copyright = "2026, Sepehr Akbarzadeh"
author = "Sepehr Akbarzadeh"
release = __version__  # Full version (e.g., "0.1.0")
# Extract major.minor version from full version (e.g., "0.1.0" -> "0.1")
version_parts = __version__.split(".")
version = ".".join(version_parts[:2]) if len(version_parts) >= 2 else __version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

# Extensions for Sphinx
extensions = [
    "myst_parser",  # Markdown support - must be loaded first for parser registration
    "sphinx.ext.autodoc",  # Auto-generate docs from docstrings
    "sphinx.ext.viewcode",  # Add source code links
    "sphinx.ext.intersphinx",  # Link to other documentation
]

# Source file extensions - support both RST and Markdown
# myst-parser v5.0+ registers the parser automatically when extension loads
# Using list format allows Sphinx to auto-detect the parser
source_suffix = [".rst", ".md"]

# Templates path
templates_path = ["_templates"]

# Exclude patterns
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "*.pyc",
    "__pycache__",
    "build",
    "make.bat",
    "Makefile",
]

# Note: Markdown files should be in docs/source/ or referenced with proper paths
# If markdown files are in parent directory, they need to be copied or moved to source/

# -- Options for Markdown (MyST Parser) --------------------------------------
# https://myst-parser.readthedocs.io/en/latest/configuration.html

myst_enable_extensions = [
    "colon_fence",  # Allow code fences with ::: syntax
    "deflist",  # Definition lists
    "fieldlist",  # Field lists
    "html_admonition",  # HTML admonitions
    "html_image",  # HTML images
    # "linkify",  # Auto-detect URLs (requires linkify-it-py package)
    "replacements",  # Common replacements (e.g., -- to em dash)
    "smartquotes",  # Smart quotes
    "strikethrough",  # Strikethrough
    "substitution",  # Substitutions
    "tasklist",  # Task lists
]

myst_heading_anchors = 3  # Generate heading anchors up to depth 3

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# Use Read the Docs theme (installed via sphinx-rtd-theme)
html_theme = "sphinx_rtd_theme"

# Theme options
html_theme_options = {
    "collapse_navigation": False,
    "display_version": True,
    "logo_only": False,
    "navigation_depth": 4,
    "prev_next_buttons_location": "bottom",
    "style_external_links": True,
    "style_nav_header_background": "#2980B9",
    "titles_only": False,
}

# Static files path
html_static_path = ["_static"]

# HTML title
html_title = f"{project} {version}"

# HTML base URL
# Set to /documentation to match FastAPI endpoint path
# This ensures all static assets and links work correctly when served from /documentation
html_baseurl = "/documentation"

# -- Options for autodoc extension --------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html

autodoc_mock_imports: list[str] = []  # Mock imports that might not be available

# -- Options for intersphinx extension ----------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "fastapi": ("https://fastapi.tiangolo.com/", None),
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/20/", None),
    # Pydantic v2 uses different URL structure
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
}

# -- Options for viewcode extension ------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/viewcode.html

viewcode_follow_imported_members = True
