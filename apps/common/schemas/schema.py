"""Pydantic schemas for common API endpoints."""

from pydantic import BaseModel, ConfigDict

from ..types import ChecksDict, EndpointDict


class HealthResponse(BaseModel):
    """Health check response model."""

    model_config = ConfigDict(from_attributes=True)

    status: str
    version: str


class LiveResponse(BaseModel):
    """Liveness check response model."""

    model_config = ConfigDict(from_attributes=True)

    status: str


class ReadyResponse(BaseModel):
    """Readiness check response model."""

    model_config = ConfigDict(from_attributes=True)

    status: str
    checks: ChecksDict


class VersionResponse(BaseModel):
    """Version information response model."""

    model_config = ConfigDict(from_attributes=True)

    version: str
    environment: str
    debug: bool


class RootResponse(BaseModel):
    """Root endpoint response model."""

    model_config = ConfigDict(from_attributes=True)

    message: str
    endpoints: EndpointDict
