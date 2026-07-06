"""Pagination utilities for SQL-level and Python-level pagination.

This module provides:
- Request-side pagination parameters (`PaginationParams`)
- Response-side pagination metadata (`PaginationMeta`) and envelope (`PaginatedResponse`)
- SQL-level pagination helpers for SQLAlchemy `select()` queries (`paginate_query`)
- Python-level pagination for in-memory lists (`paginate_list`)

Performance:
    Prefer SQL-level pagination (`paginate_query`) for database-backed list
    endpoints. Python-level pagination is appropriate only when the data is
    already in memory or cannot be paginated in SQL.

Guardrails:
    Page size is bounded by `MAX_PAGE_SIZE` to prevent accidental large
    responses.
"""

from typing import TYPE_CHECKING, Any, Generic, TypeAlias, TypeVar

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from sqlalchemy.sql import Select

from config.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

# Type aliases for pagination return types
QueryResult: TypeAlias = tuple[list[Any], int]

# Default pagination constants
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
MIN_PAGE_SIZE = 1


class PaginationParams(BaseModel):
    """Pagination parameters for request queries.

    Attributes:
        page: Page number (1-indexed)
        page_size: Number of items per page
    """

    page: int = Field(
        default=DEFAULT_PAGE,
        ge=1,
        description="Page number (1-indexed)",
    )
    page_size: int = Field(
        default=DEFAULT_PAGE_SIZE,
        ge=MIN_PAGE_SIZE,
        le=MAX_PAGE_SIZE,
        description="Number of items per page",
    )

    @field_validator("page_size")
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        """Validate page size is within allowed range."""
        if v < MIN_PAGE_SIZE:
            return MIN_PAGE_SIZE
        if v > MAX_PAGE_SIZE:
            return MAX_PAGE_SIZE
        return v

    @property
    def offset(self) -> int:
        """Calculate SQL offset from page number.

        Returns:
            SQL offset value
        """
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Get SQL limit (same as page_size).

        Returns:
            SQL limit value
        """
        return self.page_size


class PaginationMeta(BaseModel):
    """Pagination metadata for response.

    Attributes:
        page: Current page number
        page_size: Items per page
        total_items: Total number of items
        total_pages: Total number of pages
        has_next: Whether there is a next page
        has_previous: Whether there is a previous page
    """

    page: int = Field(description="Current page number")
    page_size: int = Field(description="Items per page")
    total_items: int = Field(description="Total number of items")
    total_pages: int = Field(description="Total number of pages")
    has_next: bool = Field(description="Whether there is a next page")
    has_previous: bool = Field(description="Whether there is a previous page")

    @classmethod
    def create(
        cls,
        page: int,
        page_size: int,
        total_items: int,
    ) -> "PaginationMeta":
        """Create pagination metadata.

        Args:
            page: Current page number
            page_size: Items per page
            total_items: Total number of items

        Returns:
            PaginationMeta instance
        """
        total_pages = (
            (total_items + page_size - 1) // page_size if total_items > 0 else 0
        )
        return cls(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response model.

    Attributes:
        items: List of items for current page
        meta: Pagination metadata
    """

    items: list[T] = Field(description="List of items for current page")
    meta: PaginationMeta = Field(description="Pagination metadata")

    @classmethod
    def create(
        cls,
        items: list[T],
        page: int,
        page_size: int,
        total_items: int,
    ) -> "PaginatedResponse[T]":
        """Create paginated response.

        Args:
            items: List of items for current page
            page: Current page number
            page_size: Items per page
            total_items: Total number of items

        Returns:
            PaginatedResponse instance
        """
        return cls(
            items=items,
            meta=PaginationMeta.create(
                page=page,
                page_size=page_size,
                total_items=total_items,
            ),
        )


async def paginate_query(
    db: AsyncSession,
    query: "Select[Any]",
    pagination: PaginationParams,
) -> QueryResult:
    """Paginate SQLAlchemy query at SQL level for optimal performance.

    This function performs pagination at the database level, which is
    more efficient than fetching all records and paginating in Python.

    Args:
        db: Database session
        query: SQLAlchemy select query
        pagination: Pagination parameters

    Returns:
        Tuple of (items list, total count)
    """
    # Get total count (optimized with a separate count query)
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total_items = count_result.scalar_one()

    # Apply pagination to the main query
    paginated_query = query.offset(pagination.offset).limit(pagination.limit)

    # Execute paginated query
    result = await db.execute(paginated_query)
    items = result.scalars().all()

    logger.debug(
        "Query paginated",
        page=pagination.page,
        page_size=pagination.page_size,
        total_items=total_items,
        items_returned=len(items),
    )

    return list(items), total_items


async def paginate_query_with_count_subquery(
    db: AsyncSession,
    query: "Select[Any]",
    pagination: PaginationParams,
) -> QueryResult:
    """Paginate SQLAlchemy query with count subquery.

    Alternative implementation that uses a subquery for counting.
    Use this when you need more complex counting logic.

    Args:
        db: Database session
        query: SQLAlchemy select query
        pagination: Pagination parameters

    Returns:
        Tuple of (items list, total count)
    """
    # Create count query from the same base query
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total_items = count_result.scalar_one()

    # Apply pagination
    paginated_query = query.offset(pagination.offset).limit(pagination.limit)
    result = await db.execute(paginated_query)
    items = result.scalars().all()

    logger.debug(
        "Query paginated with subquery",
        page=pagination.page,
        page_size=pagination.page_size,
        total_items=total_items,
        items_returned=len(items),
    )

    return list(items), total_items


def paginate_list(
    items: list[T],
    pagination: PaginationParams,
) -> PaginatedResponse[T]:
    """Paginate a Python list (Python-level pagination).

    Use this for paginating in-memory Python lists or when you need
    to paginate data that's already loaded.

    Args:
        items: List of items to paginate
        pagination: Pagination parameters

    Returns:
        PaginatedResponse with paginated items and metadata
    """
    total_items = len(items)
    start = pagination.offset
    end = start + pagination.limit

    paginated_items = items[start:end]

    logger.debug(
        "List paginated",
        page=pagination.page,
        page_size=pagination.page_size,
        total_items=total_items,
        items_returned=len(paginated_items),
    )

    return PaginatedResponse.create(
        items=paginated_items,
        page=pagination.page,
        page_size=pagination.page_size,
        total_items=total_items,
    )


async def get_paginated_response(
    db: AsyncSession,
    query: "Select[Any]",
    pagination: PaginationParams,
) -> PaginatedResponse[Any]:
    """Get paginated response from SQLAlchemy query.

    Convenience function that combines pagination and response creation.

    Args:
        db: Database session
        query: SQLAlchemy select query
        pagination: Pagination parameters

    Returns:
        PaginatedResponse with items and metadata
    """
    items, total_items = await paginate_query(db, query, pagination)

    return PaginatedResponse.create(
        items=items,
        page=pagination.page,
        page_size=pagination.page_size,
        total_items=total_items,
    )
