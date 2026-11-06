"""Bucket operation schemas."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BucketCreateRequest(BaseModel):
    """Bucket creation request schema."""

    bucket_name: str = Field(
        ..., description="Name of the bucket to create", min_length=3, max_length=63
    )
    region: str | None = Field(
        None, description="Optional region (uses default if not provided)"
    )


class BucketCreateResponse(BaseModel):
    """Bucket creation response schema."""

    model_config = ConfigDict(from_attributes=True)

    bucket_name: str = Field(..., description="Name of the created bucket")
    message: str = Field(..., description="Success message")


class BucketListResponse(BaseModel):
    """Bucket list response schema."""

    model_config = ConfigDict(from_attributes=True)

    buckets: list[dict[str, Any]] = Field(..., description="List of buckets")


class BucketPolicyRequest(BaseModel):
    """Bucket policy request schema."""

    policy: dict[str, Any] = Field(..., description="Bucket policy as dictionary")


class BucketPolicyResponse(BaseModel):
    """Bucket policy response schema."""

    model_config = ConfigDict(from_attributes=True)

    bucket: str = Field(..., description="Bucket name")
    policy: dict[str, Any] | None = Field(None, description="Bucket policy dictionary")


class BucketVersioningRequest(BaseModel):
    """Bucket versioning request schema."""

    status: str = Field(
        ...,
        pattern="^(Enabled|Suspended)$",
        description="Versioning status: Enabled or Suspended",
    )


class BucketVersioningResponse(BaseModel):
    """Bucket versioning response schema."""

    model_config = ConfigDict(from_attributes=True)

    bucket: str = Field(..., description="Bucket name")
    status: str = Field(..., description="Versioning status")
    mfa_delete: str | None = Field(None, description="MFA delete status")


class LifecycleRule(BaseModel):
    """Lifecycle rule schema."""

    id: str = Field(..., description="Rule identifier")
    status: str = Field(..., pattern="^(Enabled|Disabled)$", description="Rule status")
    filter: dict[str, Any] = Field(
        ..., description="Filter criteria (prefix, tags, etc.)"
    )
    expiration: dict[str, Any] | None = Field(
        None, description="Expiration configuration (days, date, etc.)"
    )
    transitions: list[dict[str, Any]] | None = Field(
        None, description="Storage class transitions"
    )
    noncurrent_version_expiration: dict[str, Any] | None = Field(
        None, description="Non-current version expiration"
    )
    noncurrent_version_transitions: list[dict[str, Any]] | None = Field(
        None, description="Non-current version transitions"
    )


class BucketLifecycleRequest(BaseModel):
    """Bucket lifecycle policy request schema."""

    rules: list[LifecycleRule] = Field(
        ..., min_length=1, description="List of lifecycle rules"
    )


class BucketLifecycleResponse(BaseModel):
    """Bucket lifecycle policy response schema."""

    model_config = ConfigDict(from_attributes=True)

    bucket: str = Field(..., description="Bucket name")
    rules: list[dict[str, Any]] = Field(..., description="Lifecycle rules")


class CORSRule(BaseModel):
    """CORS rule schema."""

    allowed_origins: list[str] = Field(
        ..., min_length=1, description="Allowed origin URLs"
    )
    allowed_methods: list[str] = Field(
        ..., min_length=1, description="Allowed HTTP methods"
    )
    allowed_headers: list[str] = Field(
        ..., description="Allowed headers (use ['*'] for all)"
    )
    expose_headers: list[str] = Field(
        default_factory=list, description="Headers to expose to client"
    )
    max_age_seconds: int = Field(
        3600, ge=0, description="Maximum age for preflight requests in seconds"
    )


class BucketCORSRequest(BaseModel):
    """Bucket CORS configuration request schema."""

    cors_rules: list[CORSRule] = Field(
        ..., min_length=1, description="List of CORS rules"
    )


class BucketCORSResponse(BaseModel):
    """Bucket CORS configuration response schema."""

    model_config = ConfigDict(from_attributes=True)

    bucket: str = Field(..., description="Bucket name")
    cors_rules: list[dict[str, Any]] = Field(..., description="CORS rules")


class BucketNotificationFilter(BaseModel):
    """Bucket notification filter schema."""

    key: dict[str, Any] = Field(
        ..., description="Key filter with filter_rules (prefix, suffix)"
    )


class BucketNotificationRequest(BaseModel):
    """Bucket notification configuration request schema."""

    events: list[str] = Field(
        ...,
        min_length=1,
        description="List of S3 events (e.g., 's3:ObjectCreated:*', 's3:ObjectRemoved:*')",
    )
    filters: list[BucketNotificationFilter] | None = Field(
        None, description="Optional filters for notifications"
    )
    webhook_url: str = Field(..., description="Webhook URL to receive notifications")
    webhook_secret: str | None = Field(
        None, description="Optional secret for webhook validation"
    )


class BucketNotificationResponse(BaseModel):
    """Bucket notification configuration response schema."""

    model_config = ConfigDict(from_attributes=True)

    bucket: str = Field(..., description="Bucket name")
    notifications: list[dict[str, Any]] = Field(
        ..., description="Notification configurations"
    )
