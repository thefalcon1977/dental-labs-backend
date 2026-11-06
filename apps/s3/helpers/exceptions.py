"""S3-specific exceptions."""

from typing import Any

from fastapi import status

from apps.core.exceptions import BaseAPIException


class S3ConnectionError(BaseAPIException):
    """S3 connection error exception."""

    def __init__(
        self,
        message: str = "Failed to connect to S3/MinIO",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details or {},
        )


class S3BucketNotFoundError(BaseAPIException):
    """Bucket not found exception."""

    def __init__(self, bucket_name: str) -> None:
        super().__init__(
            message=f"Bucket '{bucket_name}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"bucket_name": bucket_name},
        )


class S3FileNotFoundError(BaseAPIException):
    """File not found exception."""

    def __init__(self, bucket_name: str, key: str) -> None:
        super().__init__(
            message=f"File '{key}' not found in bucket '{bucket_name}'",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"bucket_name": bucket_name, "key": key},
        )


class S3UploadError(BaseAPIException):
    """File upload error exception."""

    def __init__(
        self,
        message: str = "Failed to upload file",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details or {},
        )


class S3DownloadError(BaseAPIException):
    """File download error exception."""

    def __init__(
        self,
        message: str = "Failed to download file",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details or {},
        )


class S3PermissionError(BaseAPIException):
    """S3 permission error exception."""

    def __init__(
        self, message: str = "Permission denied", details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details or {},
        )


class S3BucketExistsError(BaseAPIException):
    """Bucket already exists exception."""

    def __init__(self, bucket_name: str) -> None:
        super().__init__(
            message=f"Bucket '{bucket_name}' already exists",
            status_code=status.HTTP_409_CONFLICT,
            details={"bucket_name": bucket_name},
        )


class S3MultipartUploadError(BaseAPIException):
    """Multipart upload error exception."""

    def __init__(
        self,
        message: str = "Multipart upload failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details or {},
        )
