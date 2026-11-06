"""Business logic orchestration for S3 operations."""

import time
from contextlib import asynccontextmanager
from typing import Any

from config.logging import get_logger
from config.settings import settings

from .. import schemas
from ..repository import bll, dal
from ..types import MetadataDict, MultipartPartsList, PolicyDict

logger = get_logger(__name__)

# Import metrics only if S3 is enabled
if settings.s3.ENABLED:
    from config.metrics.s3 import (
        s3_active_operations,
        s3_bucket_operation_duration_seconds,
        s3_bucket_operations_total,
        s3_download_duration_seconds,
        s3_download_size_bytes,
        s3_downloads_total,
        s3_errors_total,
        s3_file_size_bytes,
        s3_multipart_upload_duration_seconds,
        s3_multipart_upload_part_size_bytes,
        s3_multipart_upload_parts_total,
        s3_multipart_uploads_total,
        s3_operation_duration_seconds,
        s3_operations_total,
        s3_presigned_url_generation_duration_seconds,
        s3_presigned_urls_generated_total,
        s3_upload_duration_seconds,
        s3_upload_size_bytes,
        s3_uploads_total,
    )


@asynccontextmanager
async def track_s3_operation(
    operation: str,
    bucket: str | None = None,
    track_size: bool = False,
    size: int | None = None,
):
    """Context manager to track S3 operation metrics.

    Args:
        operation: Operation name (e.g., 'upload', 'download', 'delete')
        bucket: Bucket name (optional)
        track_size: Whether to track file size
        size: File size in bytes (if known)

    Yields:
        None
    """
    if not settings.s3.ENABLED:
        yield
        return

    bucket_label = bucket or "unknown"
    start_time = time.time()
    status = "success"

    # Track active operations
    s3_active_operations.labels(operation=operation).inc()

    try:
        yield
    except Exception as e:
        status = "error"
        error_type = type(e).__name__
        s3_errors_total.labels(
            operation=operation,
            bucket=bucket_label,
            error_type=error_type,
        ).inc()
        raise
    finally:
        # Calculate duration
        duration = time.time() - start_time

        # Track operation metrics
        s3_operations_total.labels(
            operation=operation,
            bucket=bucket_label,
            status=status,
        ).inc()

        s3_operation_duration_seconds.labels(
            operation=operation,
            bucket=bucket_label,
        ).observe(duration)

        # Track file size if provided
        if track_size and size is not None:
            s3_file_size_bytes.labels(
                operation=operation,
                bucket=bucket_label,
            ).observe(size)

        # Decrement active operations
        s3_active_operations.labels(operation=operation).dec()


@asynccontextmanager
async def track_bucket_operation(operation: str):
    """Context manager to track bucket operation metrics.

    Args:
        operation: Operation name (e.g., 'create', 'delete', 'list')

    Yields:
        None
    """
    if not settings.s3.ENABLED:
        yield
        return

    start_time = time.time()
    status = "success"

    try:
        yield
    except Exception as e:
        status = "error"
        error_type = type(e).__name__
        s3_errors_total.labels(
            operation=operation,
            bucket="unknown",
            error_type=error_type,
        ).inc()
        raise
    finally:
        duration = time.time() - start_time

        s3_bucket_operations_total.labels(
            operation=operation,
            status=status,
        ).inc()

        s3_bucket_operation_duration_seconds.labels(operation=operation).observe(
            duration
        )


async def upload_file(
    bucket: str,
    key: str,
    file_data: bytes,
    content_type: str | None = None,
    metadata: MetadataDict | None = None,
) -> schemas.FileUploadResponse:
    """Upload file to S3.

    Args:
        bucket: Bucket name
        key: Object key (file path)
        file_data: File data as bytes
        content_type: Content type (MIME type)
        metadata: Optional metadata dictionary

    Returns:
        File upload response

    Raises:
        S3UploadError: If upload fails
    """
    logger.debug("Service: Uploading file", bucket=bucket, key=key)
    file_size = len(file_data)

    async with track_s3_operation(
        "upload", bucket=bucket, track_size=True, size=file_size
    ):
        start_time = time.time() if settings.s3.ENABLED else None
        status = "success"

        try:
            result = await bll.upload_file(
                bucket, key, file_data, content_type, metadata
            )

            # Track upload-specific metrics
            if settings.s3.ENABLED and start_time is not None:
                duration = time.time() - start_time
                s3_uploads_total.labels(bucket=bucket, status=status).inc()
                s3_upload_duration_seconds.labels(bucket=bucket).observe(duration)
                s3_upload_size_bytes.labels(bucket=bucket).observe(file_size)

            return schemas.FileUploadResponse(**result)
        except Exception:
            if settings.s3.ENABLED:
                status = "error"
                s3_uploads_total.labels(bucket=bucket, status=status).inc()
            raise


async def download_file(bucket: str, key: str) -> tuple[bytes, str | None]:
    """Download file from S3.

    Args:
        bucket: Bucket name
        key: Object key (file path)

    Returns:
        Tuple of (file data, content type)

    Raises:
        S3DownloadError: If download fails
    """
    logger.debug("Service: Downloading file", bucket=bucket, key=key)

    async with track_s3_operation("download", bucket=bucket):
        start_time = time.time() if settings.s3.ENABLED else None
        status = "success"

        try:
            file_data = await dal.download_file(bucket, key)
            file_size = len(file_data)

            # Get metadata for content type
            try:
                metadata = await dal.get_file_metadata(bucket, key)
                content_type = metadata.get("content_type")
            except Exception:
                content_type = None

            # Track download-specific metrics
            if settings.s3.ENABLED and start_time is not None:
                duration = time.time() - start_time
                s3_downloads_total.labels(bucket=bucket, status=status).inc()
                s3_download_duration_seconds.labels(bucket=bucket).observe(duration)
                s3_download_size_bytes.labels(bucket=bucket).observe(file_size)

            return file_data, content_type
        except Exception:
            if settings.s3.ENABLED:
                status = "error"
                s3_downloads_total.labels(bucket=bucket, status=status).inc()
            raise


async def delete_file(bucket: str, key: str) -> None:
    """Delete file from S3.

    Args:
        bucket: Bucket name
        key: Object key (file path)

    Raises:
        S3DownloadError: If deletion fails
    """
    logger.debug("Service: Deleting file", bucket=bucket, key=key)
    async with track_s3_operation("delete", bucket=bucket):
        await bll.delete_file(bucket, key)


async def list_files(
    bucket: str,
    prefix: str = "",
    max_keys: int = 1000,
    continuation_token: str | None = None,
) -> schemas.FileListResponse:
    """List files in bucket.

    Args:
        bucket: Bucket name
        prefix: Prefix to filter files
        max_keys: Maximum number of keys to return
        continuation_token: Token for pagination

    Returns:
        File list response

    Raises:
        S3DownloadError: If listing fails
    """
    logger.debug("Service: Listing files", bucket=bucket, prefix=prefix)
    async with track_s3_operation("list", bucket=bucket):
        result = await dal.list_files(bucket, prefix, max_keys, continuation_token)
        return schemas.FileListResponse(**result)


async def get_file_metadata(bucket: str, key: str) -> schemas.FileMetadataResponse:
    """Get file metadata.

    Args:
        bucket: Bucket name
        key: Object key (file path)

    Returns:
        File metadata response

    Raises:
        S3DownloadError: If metadata retrieval fails
    """
    logger.debug("Service: Getting file metadata", bucket=bucket, key=key)
    async with track_s3_operation("get_metadata", bucket=bucket):
        result = await dal.get_file_metadata(bucket, key)
        return schemas.FileMetadataResponse(**result)


async def generate_presigned_url(
    bucket: str,
    key: str,
    expiration: int = 3600,
    http_method: str = "GET",
) -> schemas.PresignedUrlResponse:
    """Generate presigned URL for file access.

    Args:
        bucket: Bucket name
        key: Object key (file path)
        expiration: URL expiration time in seconds
        http_method: HTTP method (GET or PUT)

    Returns:
        Presigned URL response

    Raises:
        S3DownloadError: If URL generation fails
    """
    logger.debug(
        "Service: Generating presigned URL",
        bucket=bucket,
        key=key,
        expiration=expiration,
    )

    async with track_s3_operation("presigned_url", bucket=bucket):
        start_time = time.time() if settings.s3.ENABLED else None

        url = await bll.generate_presigned_url(bucket, key, expiration, http_method)

        # Track presigned URL metrics
        if settings.s3.ENABLED and start_time is not None:
            duration = time.time() - start_time
            s3_presigned_urls_generated_total.labels(
                bucket=bucket, http_method=http_method
            ).inc()
            s3_presigned_url_generation_duration_seconds.labels(bucket=bucket).observe(
                duration
            )

        return schemas.PresignedUrlResponse(
            url=url,
            bucket=bucket,
            key=key,
            expiration=expiration,
        )


async def initiate_multipart_upload(
    bucket: str,
    key: str,
    content_type: str | None = None,
    metadata: MetadataDict | None = None,
) -> schemas.MultipartUploadInitResponse:
    """Initiate multipart upload.

    Args:
        bucket: Bucket name
        key: Object key (file path)
        content_type: Content type (MIME type)
        metadata: Optional metadata dictionary

    Returns:
        Multipart upload initiation response

    Raises:
        S3MultipartUploadError: If initiation fails
    """
    logger.debug("Service: Initiating multipart upload", bucket=bucket, key=key)

    async with track_s3_operation("multipart_init", bucket=bucket):
        start_time = time.time() if settings.s3.ENABLED else None
        status = "success"

        try:
            result = await bll.create_multipart_upload(
                bucket, key, content_type, metadata
            )

            if settings.s3.ENABLED and start_time is not None:
                duration = time.time() - start_time
                s3_multipart_uploads_total.labels(
                    operation="init", bucket=bucket, status=status
                ).inc()
                s3_multipart_upload_duration_seconds.labels(
                    operation="init", bucket=bucket
                ).observe(duration)

            return schemas.MultipartUploadInitResponse(**result)
        except Exception:
            if settings.s3.ENABLED:
                status = "error"
                s3_multipart_uploads_total.labels(
                    operation="init", bucket=bucket, status=status
                ).inc()
            raise


async def upload_part(
    bucket: str,
    key: str,
    upload_id: str,
    part_number: int,
    part_data: bytes,
) -> schemas.MultipartUploadPartResponse:
    """Upload part in multipart upload.

    Args:
        bucket: Bucket name
        key: Object key (file path)
        upload_id: Multipart upload ID
        part_number: Part number (1-indexed)
        part_data: Part data as bytes

    Returns:
        Multipart upload part response

    Raises:
        S3MultipartUploadError: If part upload fails
    """
    logger.debug(
        "Service: Uploading part", bucket=bucket, key=key, part_number=part_number
    )
    part_size = len(part_data)

    async with track_s3_operation("multipart_upload_part", bucket=bucket):
        start_time = time.time() if settings.s3.ENABLED else None
        status = "success"

        try:
            result = await bll.upload_part(
                bucket, key, upload_id, part_number, part_data
            )

            if settings.s3.ENABLED and start_time is not None:
                duration = time.time() - start_time
                s3_multipart_upload_parts_total.labels(
                    bucket=bucket, status=status
                ).inc()
                s3_multipart_upload_duration_seconds.labels(
                    operation="upload_part", bucket=bucket
                ).observe(duration)
                s3_multipart_upload_part_size_bytes.labels(bucket=bucket).observe(
                    part_size
                )

            return schemas.MultipartUploadPartResponse(**result)
        except Exception:
            if settings.s3.ENABLED:
                status = "error"
                s3_multipart_upload_parts_total.labels(
                    bucket=bucket, status=status
                ).inc()
            raise


async def complete_multipart_upload(
    bucket: str,
    key: str,
    upload_id: str,
    parts: MultipartPartsList,
) -> schemas.MultipartUploadCompleteResponse:
    """Complete multipart upload.

    Args:
        bucket: Bucket name
        key: Object key (file path)
        upload_id: Multipart upload ID
        parts: List of parts with ETag and part number

    Returns:
        Multipart upload completion response

    Raises:
        S3MultipartUploadError: If completion fails
    """
    logger.debug(
        "Service: Completing multipart upload",
        bucket=bucket,
        key=key,
        upload_id=upload_id,
    )

    async with track_s3_operation("multipart_complete", bucket=bucket):
        start_time = time.time() if settings.s3.ENABLED else None
        status = "success"

        try:
            result = await bll.complete_multipart_upload(bucket, key, upload_id, parts)

            if settings.s3.ENABLED and start_time is not None:
                duration = time.time() - start_time
                s3_multipart_uploads_total.labels(
                    operation="complete", bucket=bucket, status=status
                ).inc()
                s3_multipart_upload_duration_seconds.labels(
                    operation="complete", bucket=bucket
                ).observe(duration)

            return schemas.MultipartUploadCompleteResponse(**result)
        except Exception:
            if settings.s3.ENABLED:
                status = "error"
                s3_multipart_uploads_total.labels(
                    operation="complete", bucket=bucket, status=status
                ).inc()
            raise


async def abort_multipart_upload(bucket: str, key: str, upload_id: str) -> None:
    """Abort multipart upload.

    Args:
        bucket: Bucket name
        key: Object key (file path)
        upload_id: Multipart upload ID

    Raises:
        S3MultipartUploadError: If abort fails
    """
    logger.debug(
        "Service: Aborting multipart upload",
        bucket=bucket,
        key=key,
        upload_id=upload_id,
    )

    async with track_s3_operation("multipart_abort", bucket=bucket):
        start_time = time.time() if settings.s3.ENABLED else None
        status = "success"

        try:
            await bll.abort_multipart_upload(bucket, key, upload_id)

            if settings.s3.ENABLED and start_time is not None:
                duration = time.time() - start_time
                s3_multipart_uploads_total.labels(
                    operation="abort", bucket=bucket, status=status
                ).inc()
                s3_multipart_upload_duration_seconds.labels(
                    operation="abort", bucket=bucket
                ).observe(duration)
        except Exception:
            if settings.s3.ENABLED:
                status = "error"
                s3_multipart_uploads_total.labels(
                    operation="abort", bucket=bucket, status=status
                ).inc()
            raise


async def create_bucket(
    bucket_name: str, region: str | None = None
) -> schemas.BucketCreateResponse:
    """Create bucket.

    Args:
        bucket_name: Name of the bucket to create
        region: Optional region (uses default if not provided)

    Returns:
        Bucket creation response

    Raises:
        S3BucketExistsError: If bucket already exists
        S3UploadError: If creation fails
    """
    logger.debug("Service: Creating bucket", bucket_name=bucket_name)
    async with track_bucket_operation("create"):
        await bll.create_bucket(bucket_name, region)
        return schemas.BucketCreateResponse(
            bucket_name=bucket_name,
            message=f"Bucket '{bucket_name}' created successfully",
        )


async def delete_bucket(bucket_name: str) -> None:
    """Delete bucket.

    Args:
        bucket_name: Name of the bucket to delete

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3UploadError: If deletion fails
    """
    logger.debug("Service: Deleting bucket", bucket_name=bucket_name)
    async with track_bucket_operation("delete"):
        await bll.delete_bucket(bucket_name)


async def list_buckets() -> schemas.BucketListResponse:
    """List all buckets.

    Returns:
        Bucket list response

    Raises:
        S3DownloadError: If listing fails
    """
    logger.debug("Service: Listing buckets")
    async with track_bucket_operation("list"):
        buckets = await dal.list_buckets()
        return schemas.BucketListResponse(buckets=buckets)


async def bucket_exists(bucket_name: str) -> bool:
    """Check if bucket exists.

    Args:
        bucket_name: Name of the bucket to check

    Returns:
        True if bucket exists, False otherwise

    Raises:
        S3DownloadError: If check fails
    """
    logger.debug("Service: Checking bucket existence", bucket_name=bucket_name)
    async with track_bucket_operation("exists"):
        return await dal.bucket_exists(bucket_name)


async def get_bucket_policy(bucket_name: str) -> schemas.BucketPolicyResponse:
    """Get bucket policy.

    Args:
        bucket_name: Name of the bucket

    Returns:
        Bucket policy response

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3DownloadError: If retrieval fails
    """
    logger.debug("Service: Getting bucket policy", bucket_name=bucket_name)
    async with track_bucket_operation("get_policy"):
        result = await dal.get_bucket_policy(bucket_name)
        return schemas.BucketPolicyResponse(**result)


async def set_bucket_policy(bucket_name: str, policy: PolicyDict) -> None:
    """Set bucket policy.

    Args:
        bucket_name: Name of the bucket
        policy: Policy dictionary to set

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3UploadError: If setting fails
    """
    logger.debug("Service: Setting bucket policy", bucket_name=bucket_name)
    async with track_bucket_operation("set_policy"):
        await bll.set_bucket_policy(bucket_name, policy)


async def copy_file(
    source_bucket: str,
    source_key: str,
    destination_bucket: str,
    destination_key: str,
    metadata: MetadataDict | None = None,
) -> schemas.FileCopyResponse:
    """Copy file within or between buckets.

    Args:
        source_bucket: Source bucket name
        source_key: Source file key (path)
        destination_bucket: Destination bucket name
        destination_key: Destination file key (path)
        metadata: Optional new metadata for copied file

    Returns:
        File copy response

    Raises:
        S3UploadError: If copy fails
        S3FileNotFoundError: If source file doesn't exist
        S3BucketNotFoundError: If bucket doesn't exist
    """
    logger.debug(
        "Service: Copying file",
        source_bucket=source_bucket,
        source_key=source_key,
        destination_bucket=destination_bucket,
        destination_key=destination_key,
    )
    async with track_s3_operation("copy", bucket=source_bucket):
        result = await bll.copy_file(
            source_bucket, source_key, destination_bucket, destination_key, metadata
        )
        return schemas.FileCopyResponse(**result)


async def move_file(
    source_bucket: str,
    source_key: str,
    destination_bucket: str,
    destination_key: str,
    metadata: MetadataDict | None = None,
) -> schemas.FileMoveResponse:
    """Move file within or between buckets.

    Args:
        source_bucket: Source bucket name
        source_key: Source file key (path)
        destination_bucket: Destination bucket name
        destination_key: Destination file key (path)
        metadata: Optional new metadata for moved file

    Returns:
        File move response

    Raises:
        S3UploadError: If move fails
        S3FileNotFoundError: If source file doesn't exist
        S3BucketNotFoundError: If bucket doesn't exist
    """
    logger.debug(
        "Service: Moving file",
        source_bucket=source_bucket,
        source_key=source_key,
        destination_bucket=destination_bucket,
        destination_key=destination_key,
    )
    async with track_s3_operation("move", bucket=source_bucket):
        result = await bll.move_file(
            source_bucket, source_key, destination_bucket, destination_key, metadata
        )
        return schemas.FileMoveResponse(**result)


async def batch_delete_files(
    bucket: str, keys: list[str]
) -> schemas.BatchDeleteResponse:
    """Delete multiple files in a single request.

    Args:
        bucket: Bucket name
        keys: List of file keys to delete

    Returns:
        Batch delete response

    Raises:
        S3DownloadError: If deletion fails
        S3BucketNotFoundError: If bucket doesn't exist
    """
    logger.debug("Service: Batch deleting files", bucket=bucket, count=len(keys))
    async with track_s3_operation("batch_delete", bucket=bucket):
        result = await bll.batch_delete_files(bucket, keys)
        return schemas.BatchDeleteResponse(**result)


async def delete_files_by_prefix(
    bucket: str, prefix: str, max_keys: int = 1000
) -> schemas.DeletePrefixResponse:
    """Delete files by prefix.

    Args:
        bucket: Bucket name
        prefix: Prefix to match files for deletion
        max_keys: Maximum number of keys to delete

    Returns:
        Delete prefix response

    Raises:
        S3DownloadError: If deletion fails
        S3BucketNotFoundError: If bucket doesn't exist
    """
    logger.debug("Service: Deleting files by prefix", bucket=bucket, prefix=prefix)
    async with track_s3_operation("delete_prefix", bucket=bucket):
        # List files with prefix
        file_list = await dal.list_files(bucket, prefix, max_keys, None)
        keys = [file["key"] for file in file_list["files"]]

        if not keys:
            return schemas.DeletePrefixResponse(
                bucket=bucket, prefix=prefix, deleted_count=0, deleted_keys=[]
            )

        # Batch delete
        result = await bll.batch_delete_files(bucket, keys)
        return schemas.DeletePrefixResponse(
            bucket=bucket,
            prefix=prefix,
            deleted_count=len(result["deleted"]),
            deleted_keys=result["deleted"],
        )


async def list_file_versions(bucket: str, key: str) -> schemas.FileVersionsResponse:
    """List all versions of a file.

    Args:
        bucket: Bucket name
        key: File key (path)

    Returns:
        File versions response

    Raises:
        S3DownloadError: If listing fails
        S3BucketNotFoundError: If bucket doesn't exist
    """
    logger.debug("Service: Listing file versions", bucket=bucket, key=key)
    async with track_s3_operation("list_versions", bucket=bucket):
        result = await dal.list_object_versions(bucket, key)
        return schemas.FileVersionsResponse(**result)


async def download_file_version(
    bucket: str, key: str, version_id: str
) -> tuple[bytes, str | None]:
    """Download a specific version of a file.

    Args:
        bucket: Bucket name
        key: File key (path)
        version_id: Version ID to download

    Returns:
        Tuple of (file data, content type)

    Raises:
        S3DownloadError: If download fails
        S3FileNotFoundError: If version doesn't exist
        S3BucketNotFoundError: If bucket doesn't exist
    """
    logger.debug(
        "Service: Downloading file version",
        bucket=bucket,
        key=key,
        version_id=version_id,
    )
    async with track_s3_operation("download_version", bucket=bucket):
        file_data = await dal.download_file_version(bucket, key, version_id)

        # Get metadata for content type
        try:
            metadata = await dal.get_file_metadata(bucket, key)
            content_type = metadata.get("content_type")
        except Exception:
            content_type = None

        return file_data, content_type


async def delete_file_version(bucket: str, key: str, version_id: str) -> None:
    """Delete a specific version of a file.

    Args:
        bucket: Bucket name
        key: File key (path)
        version_id: Version ID to delete

    Raises:
        S3DownloadError: If deletion fails
        S3FileNotFoundError: If version doesn't exist
        S3BucketNotFoundError: If bucket doesn't exist
    """
    logger.debug(
        "Service: Deleting file version", bucket=bucket, key=key, version_id=version_id
    )
    async with track_s3_operation("delete_version", bucket=bucket):
        await bll.delete_file_version(bucket, key, version_id)


async def get_bucket_versioning(
    bucket_name: str,
) -> schemas.BucketVersioningResponse:
    """Get bucket versioning configuration.

    Args:
        bucket_name: Name of the bucket

    Returns:
        Bucket versioning response

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3DownloadError: If retrieval fails
    """
    logger.debug("Service: Getting bucket versioning", bucket_name=bucket_name)
    async with track_bucket_operation("get_versioning"):
        result = await dal.get_bucket_versioning(bucket_name)
        return schemas.BucketVersioningResponse(**result)


async def set_bucket_versioning(
    bucket_name: str, status: str
) -> schemas.BucketVersioningResponse:
    """Set bucket versioning configuration.

    Args:
        bucket_name: Name of the bucket
        status: Versioning status ('Enabled' or 'Suspended')

    Returns:
        Bucket versioning response

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3UploadError: If setting fails
    """
    logger.debug(
        "Service: Setting bucket versioning", bucket_name=bucket_name, status=status
    )
    async with track_bucket_operation("set_versioning"):
        await bll.set_bucket_versioning(bucket_name, status)
        result = await dal.get_bucket_versioning(bucket_name)
        return schemas.BucketVersioningResponse(**result)


async def get_bucket_lifecycle(
    bucket_name: str,
) -> schemas.BucketLifecycleResponse:
    """Get bucket lifecycle configuration.

    Args:
        bucket_name: Name of the bucket

    Returns:
        Bucket lifecycle response

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3DownloadError: If retrieval fails
    """
    logger.debug("Service: Getting bucket lifecycle", bucket_name=bucket_name)
    async with track_bucket_operation("get_lifecycle"):
        result = await dal.get_bucket_lifecycle(bucket_name)
        return schemas.BucketLifecycleResponse(**result)


async def set_bucket_lifecycle(
    bucket_name: str, rules: list[dict[str, Any]]
) -> schemas.BucketLifecycleResponse:
    """Set bucket lifecycle configuration.

    Args:
        bucket_name: Name of the bucket
        rules: List of lifecycle rules

    Returns:
        Bucket lifecycle response

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3UploadError: If setting fails
    """
    logger.debug("Service: Setting bucket lifecycle", bucket_name=bucket_name)
    async with track_bucket_operation("set_lifecycle"):
        await bll.set_bucket_lifecycle(bucket_name, rules)
        result = await dal.get_bucket_lifecycle(bucket_name)
        return schemas.BucketLifecycleResponse(**result)


async def get_bucket_cors(bucket_name: str) -> schemas.BucketCORSResponse:
    """Get bucket CORS configuration.

    Args:
        bucket_name: Name of the bucket

    Returns:
        Bucket CORS response

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3DownloadError: If retrieval fails
    """
    logger.debug("Service: Getting bucket CORS", bucket_name=bucket_name)
    async with track_bucket_operation("get_cors"):
        result = await dal.get_bucket_cors(bucket_name)
        return schemas.BucketCORSResponse(**result)


async def set_bucket_cors(
    bucket_name: str, cors_rules: list[dict[str, Any]]
) -> schemas.BucketCORSResponse:
    """Set bucket CORS configuration.

    Args:
        bucket_name: Name of the bucket
        cors_rules: List of CORS rules

    Returns:
        Bucket CORS response

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3UploadError: If setting fails
    """
    logger.debug("Service: Setting bucket CORS", bucket_name=bucket_name)
    async with track_bucket_operation("set_cors"):
        await bll.set_bucket_cors(bucket_name, cors_rules)
        result = await dal.get_bucket_cors(bucket_name)
        return schemas.BucketCORSResponse(**result)


async def get_bucket_notifications(
    bucket_name: str,
) -> schemas.BucketNotificationResponse:
    """Get bucket notification configuration.

    Args:
        bucket_name: Name of the bucket

    Returns:
        Bucket notification response

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3DownloadError: If retrieval fails
    """
    logger.debug("Service: Getting bucket notifications", bucket_name=bucket_name)
    async with track_bucket_operation("get_notifications"):
        result = await dal.get_bucket_notifications(bucket_name)
        return schemas.BucketNotificationResponse(**result)


async def set_bucket_notifications(
    bucket_name: str,
    events: list[str],
    filters: list[dict[str, Any]] | None = None,
    webhook_url: str | None = None,
) -> schemas.BucketNotificationResponse:
    """Set bucket notification configuration.

    Args:
        bucket_name: Name of the bucket
        events: List of S3 events
        filters: Optional filters for notifications
        webhook_url: Optional webhook URL (requires SNS/Lambda setup)

    Returns:
        Bucket notification response

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3UploadError: If setting fails
    """
    logger.debug("Service: Setting bucket notifications", bucket_name=bucket_name)
    async with track_bucket_operation("set_notifications"):
        await bll.set_bucket_notifications(bucket_name, events, filters, webhook_url)
        result = await dal.get_bucket_notifications(bucket_name)
        return schemas.BucketNotificationResponse(**result)
