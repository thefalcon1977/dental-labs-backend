"""File operation schemas."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FileUploadResponse(BaseModel):
    """File upload response schema."""

    model_config = ConfigDict(from_attributes=True)

    bucket: str = Field(..., description="Bucket name")
    key: str = Field(..., description="File key (path)")
    content_type: str | None = Field(None, description="Content type (MIME type)")


class FileDownloadResponse(BaseModel):
    """File download response schema."""

    model_config = ConfigDict(from_attributes=True)

    bucket: str = Field(..., description="Bucket name")
    key: str = Field(..., description="File key (path)")
    content_type: str | None = Field(None, description="Content type (MIME type)")
    size: int = Field(..., description="File size in bytes")


class FileListResponse(BaseModel):
    """File list response schema."""

    model_config = ConfigDict(from_attributes=True)

    files: list[dict[str, Any]] = Field(..., description="List of files")
    is_truncated: bool = Field(..., description="Whether there are more files")
    next_continuation_token: str | None = Field(None, description="Token for next page")


class FileMetadataResponse(BaseModel):
    """File metadata response schema."""

    model_config = ConfigDict(from_attributes=True)

    key: str = Field(..., description="File key (path)")
    bucket: str = Field(..., description="Bucket name")
    size: int = Field(..., description="File size in bytes")
    content_type: str | None = Field(None, description="Content type (MIME type)")
    last_modified: str | None = Field(
        None, description="Last modified timestamp (ISO format)"
    )
    etag: str = Field(..., description="File ETag")
    metadata: dict[str, str] = Field(
        default_factory=dict, description="Custom metadata"
    )


class PresignedUrlRequest(BaseModel):
    """Presigned URL request schema."""

    bucket: str = Field(..., description="Bucket name")
    key: str = Field(..., description="File key (path)")
    expiration: int = Field(
        3600, ge=1, le=604800, description="URL expiration in seconds (1-604800)"
    )
    http_method: str = Field(
        "GET", pattern="^(GET|PUT)$", description="HTTP method (GET or PUT)"
    )


class PresignedUrlResponse(BaseModel):
    """Presigned URL response schema."""

    model_config = ConfigDict(from_attributes=True)

    url: str = Field(..., description="Presigned URL")
    bucket: str = Field(..., description="Bucket name")
    key: str = Field(..., description="File key (path)")
    expiration: int = Field(..., description="URL expiration in seconds")


class MultipartUploadInitRequest(BaseModel):
    """Multipart upload initiation request schema."""

    bucket: str = Field(..., description="Bucket name")
    key: str = Field(..., description="File key (path)")
    content_type: str | None = Field(None, description="Content type (MIME type)")
    metadata: dict[str, str] = Field(
        default_factory=dict, description="Custom metadata"
    )


class MultipartUploadInitResponse(BaseModel):
    """Multipart upload initiation response schema."""

    model_config = ConfigDict(from_attributes=True)

    bucket: str = Field(..., description="Bucket name")
    key: str = Field(..., description="File key (path)")
    upload_id: str = Field(..., description="Multipart upload ID")


class MultipartUploadPartRequest(BaseModel):
    """Multipart upload part request schema."""

    bucket: str = Field(..., description="Bucket name")
    key: str = Field(..., description="File key (path)")
    upload_id: str = Field(..., description="Multipart upload ID")
    part_number: int = Field(..., ge=1, le=10000, description="Part number (1-10000)")


class MultipartUploadPartResponse(BaseModel):
    """Multipart upload part response schema."""

    model_config = ConfigDict(from_attributes=True)

    part_number: int = Field(..., description="Part number")
    etag: str = Field(..., description="Part ETag")


class MultipartUploadCompleteRequest(BaseModel):
    """Multipart upload completion request schema."""

    bucket: str = Field(..., description="Bucket name")
    key: str = Field(..., description="File key (path)")
    upload_id: str = Field(..., description="Multipart upload ID")
    parts: list[dict[str, Any]] = Field(
        ...,
        description="List of parts with 'part_number' and 'etag'",
        min_length=1,
    )


class MultipartUploadCompleteResponse(BaseModel):
    """Multipart upload completion response schema."""

    model_config = ConfigDict(from_attributes=True)

    bucket: str = Field(..., description="Bucket name")
    key: str = Field(..., description="File key (path)")
    etag: str = Field(..., description="Complete file ETag")


class FileCopyRequest(BaseModel):
    """File copy request schema."""

    source_bucket: str = Field(..., description="Source bucket name")
    source_key: str = Field(..., description="Source file key (path)")
    destination_bucket: str = Field(..., description="Destination bucket name")
    destination_key: str = Field(..., description="Destination file key (path)")
    metadata: dict[str, str] = Field(
        default_factory=dict, description="Optional new metadata for copied file"
    )


class FileCopyResponse(BaseModel):
    """File copy response schema."""

    model_config = ConfigDict(from_attributes=True)

    source_bucket: str = Field(..., description="Source bucket name")
    source_key: str = Field(..., description="Source file key")
    destination_bucket: str = Field(..., description="Destination bucket name")
    destination_key: str = Field(..., description="Destination file key")
    etag: str = Field(..., description="ETag of copied file")


class FileMoveRequest(BaseModel):
    """File move request schema."""

    source_bucket: str = Field(..., description="Source bucket name")
    source_key: str = Field(..., description="Source file key (path)")
    destination_bucket: str = Field(..., description="Destination bucket name")
    destination_key: str = Field(..., description="Destination file key (path)")
    metadata: dict[str, str] = Field(
        default_factory=dict, description="Optional new metadata for moved file"
    )


class FileMoveResponse(BaseModel):
    """File move response schema."""

    model_config = ConfigDict(from_attributes=True)

    source_bucket: str = Field(..., description="Source bucket name")
    source_key: str = Field(..., description="Source file key")
    destination_bucket: str = Field(..., description="Destination bucket name")
    destination_key: str = Field(..., description="Destination file key")
    etag: str = Field(..., description="ETag of moved file")


class BatchDeleteRequest(BaseModel):
    """Batch delete request schema."""

    bucket: str = Field(..., description="Bucket name")
    keys: list[str] = Field(
        ..., min_length=1, max_length=1000, description="List of file keys to delete"
    )


class BatchDeleteResponse(BaseModel):
    """Batch delete response schema."""

    model_config = ConfigDict(from_attributes=True)

    bucket: str = Field(..., description="Bucket name")
    deleted: list[str] = Field(..., description="List of successfully deleted keys")
    errors: list[dict[str, Any]] = Field(
        default_factory=list, description="List of errors for failed deletions"
    )


class DeletePrefixRequest(BaseModel):
    """Delete by prefix request schema."""

    bucket: str = Field(..., description="Bucket name")
    prefix: str = Field(..., description="Prefix to match files for deletion")
    max_keys: int = Field(
        1000, ge=1, le=10000, description="Maximum number of keys to delete"
    )


class DeletePrefixResponse(BaseModel):
    """Delete by prefix response schema."""

    model_config = ConfigDict(from_attributes=True)

    bucket: str = Field(..., description="Bucket name")
    prefix: str = Field(..., description="Prefix used for deletion")
    deleted_count: int = Field(..., description="Number of files deleted")
    deleted_keys: list[str] = Field(..., description="List of deleted keys")


class FileVersionInfo(BaseModel):
    """File version information schema."""

    model_config = ConfigDict(from_attributes=True)

    version_id: str = Field(..., description="Version ID")
    is_latest: bool = Field(..., description="Whether this is the latest version")
    last_modified: str = Field(..., description="Last modified timestamp (ISO format)")
    size: int = Field(..., description="File size in bytes")
    etag: str = Field(..., description="File ETag")


class FileVersionsResponse(BaseModel):
    """File versions response schema."""

    model_config = ConfigDict(from_attributes=True)

    bucket: str = Field(..., description="Bucket name")
    key: str = Field(..., description="File key")
    versions: list[FileVersionInfo] = Field(..., description="List of file versions")


class FileDownloadVersionRequest(BaseModel):
    """File download with version request schema."""

    bucket: str = Field(..., description="Bucket name")
    key: str = Field(..., description="File key (path)")
    version_id: str = Field(..., description="Version ID to download")
