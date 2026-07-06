"""Async database configuration and session management using SQLAlchemy 2.0.

This module provides:
- Base class for all database models
- DatabaseManager for connection pool management
- Session dependency injection for FastAPI routes
- Health check utilities for database connectivity

All database operations use async SQLAlchemy 2.0 syntax with proper connection
pooling, pre-ping for connection health, and automatic session cleanup.
"""

import asyncio
from typing import TYPE_CHECKING, AsyncGenerator

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from config.settings import settings

if TYPE_CHECKING:
    from fastapi import FastAPI


class Base(DeclarativeBase):
    """Base class for all database models using SQLAlchemy 2.0.

    All application models should inherit from this base class to ensure
    compatibility with SQLAlchemy 2.0 async operations and proper type hints.

    Example:
        ```python
        from apps.core.db import Base
        from sqlalchemy.orm import Mapped, mapped_column
        from sqlalchemy import String

        class User(Base):
            __tablename__ = "users"
            id: Mapped[str] = mapped_column(String(36), primary_key=True)
        ```
    """


class DatabaseManager:
    """Database manager for handling async database connections.

    Manages the database connection pool, session factory, and provides
    utilities for database operations. The manager is initialized during
    application startup and stored in the FastAPI app state.

    Attributes:
        _engine: SQLAlchemy async engine instance
        _session_maker: Async session factory for creating database sessions
    """

    def __init__(self) -> None:
        """Initialize database manager.

        Creates a new database manager instance. The actual database connection
        is established when `initialize()` is called.
        """
        self._engine: AsyncEngine | None = None
        self._session_maker: async_sessionmaker[AsyncSession] | None = None

    def get_database_url(self) -> str:
        """Get database URL from settings.

        Constructs the database connection URL from configuration settings.

        Returns:
            Database connection URL string

        Raises:
            RuntimeError: If database is not enabled in settings
        """
        if not settings.database.ENABLED:
            raise RuntimeError("Database is not enabled in settings")

        return (
            f"{settings.database.DRIVER}://"
            f"{settings.database.USER}:{settings.database.PASSWORD}@"
            f"{settings.database.HOST}:{settings.database.PORT}/"
            f"{settings.database.NAME}"
        )

    async def initialize(self) -> None:
        """Initialize database connection.

        Creates the async engine and session factory with connection pooling.
        This method is idempotent - calling it multiple times has no effect
        if already initialized.

        The connection pool is configured with:
        - Pool size and max overflow from settings
        - Pre-ping enabled to check connection health
        - Connection recycling to prevent stale connections
        - Echo mode for SQL logging (if enabled in settings)
        """
        if not settings.database.ENABLED:
            return

        if self._engine is not None:
            return  # Already initialized

        database_url = self.get_database_url()

        self._engine = create_async_engine(
            database_url,
            pool_size=settings.database.POOL_SIZE,
            max_overflow=settings.database.MAX_OVERFLOW,
            pool_pre_ping=settings.database.POOL_PRE_PING,
            pool_recycle=settings.database.POOL_RECYCLE,
            pool_timeout=settings.database.POOL_TIMEOUT,
            echo=settings.database.ECHO,
        )

        self._session_maker = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        if not settings.database.DB_FIRST:
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

    async def close(self) -> None:
        """Close database connection.

        Disposes of the database engine and closes all connection pools.
        This should be called during application shutdown to properly
        clean up database resources.
        """
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_maker = None

    def get_session_maker(self) -> async_sessionmaker[AsyncSession]:
        """Get session maker for creating database sessions.

        Returns:
            Async session factory for creating database sessions

        Raises:
            RuntimeError: If database manager has not been initialized
        """
        if self._session_maker is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._session_maker

    def get_engine(self) -> AsyncEngine:
        """Get database engine instance.

        Returns:
            SQLAlchemy async engine instance

        Raises:
            RuntimeError: If database manager has not been initialized
        """
        if self._engine is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._engine

    async def check_health(self, timeout: float = 2.0) -> bool:
        """Check database connection health with timeout.

        Args:
            timeout: Maximum time to wait for health check (seconds)

        Returns:
            True if database is healthy, False otherwise
        """
        if not settings.database.ENABLED or self._engine is None:
            return False

        try:
            # Use a timeout to prevent hanging on slow/unresponsive databases
            async with asyncio.timeout(timeout):
                async with self._engine.begin() as conn:
                    await conn.execute(text("SELECT 1"))
            return True
        except (Exception, asyncio.TimeoutError):
            return False


def get_db_manager_from_app(app: "FastAPI") -> DatabaseManager:
    """Get database manager from FastAPI app state.

    Retrieves the DatabaseManager instance that was stored in the FastAPI
    application state during startup.

    Args:
        app: FastAPI application instance

    Returns:
        DatabaseManager instance from app state

    Raises:
        RuntimeError: If database manager is not initialized in app state
    """
    if not hasattr(app.state, "db_manager"):
        raise RuntimeError("Database manager not initialized in app state")
    return app.state.db_manager


async def get_db(
    request: Request,
) -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session.

    FastAPI dependency that provides a database session for route handlers.
    The session is automatically closed after the request completes.

    Usage:
        ```python
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            # Use db session here
            pass
        ```

    Args:
        request: FastAPI request object

    Yields:
        AsyncSession: Database session for the current request
    """
    db_manager = get_db_manager_from_app(request.app)
    session_maker = db_manager.get_session_maker()
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_db_health(app: "FastAPI") -> bool:
    """Check database connection health.

    Performs a simple health check by executing a SELECT 1 query against
    the database. Uses the default timeout from DatabaseManager.check_health().

    Args:
        app: FastAPI application instance

    Returns:
        True if database is healthy and responsive, False otherwise
    """
    db_manager = get_db_manager_from_app(app)
    return await db_manager.check_health()
