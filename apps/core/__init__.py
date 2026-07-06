"""Core package for shared application functionality.

This package provides core functionality shared across all applications in the
microservices template, including:

- Application factory for FastAPI app creation
- Database management and session handling
- Exception handling and error responses
- Base models and mixins for database models
- System information utilities
- Version management
- Type definitions
- Pagination utilities
- CLI command package (Typer-based) used by manage.py

Modules:
    app_factory: FastAPI application factory with multi-app support
    db: Async database configuration and session management
    exceptions: Hierarchical exception handlers for the application
    models: Base models and mixins using SQLAlchemy 2.0
    system_info: System information utilities for startup information
    version: Single source of truth for application version
    types: Type aliases for core module
    utils: Utility functions (pagination, etc.)
    cli: Typer-based CLI commands (invoked via manage.py)
"""

__all__ = [
    "db",
    "version",
]
