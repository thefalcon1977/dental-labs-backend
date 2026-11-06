"""Business Logic Layer for S3 write operations."""

from typing import Any

from config.logging import get_logger

from ..types import (
    MetadataDict,
    MultipartCompleteResultDict,
    MultipartInitResultDict,
    MultipartPartResultDict,
    MultipartPartsList,
    PolicyDict,
    UploadResultDict,
)
from ..utils.s3_client import get_s3_client

logger = get_logger(__name__)


async def upload_file(
    bucket: str,
    key: str,
    file_data: bytes,
    content_type: str | None = None,
    metadata: MetadataDict | None = None,
) -> UploadResultDict:
    """Upload file to S3.

    Creates a new file in S3 bucket. This is a write operation
    that modifies S3 state.

    Args:
        bucket: Bucket name
        key: Object key (file path)
        file_data: File data as bytes
        content_type: Content type (MIME type)
        metadata: Optional metadata dictionary

    Returns:
        Dictionary with upload information

    Raises:
        S3UploadError: If upload fails
        S3BucketNotFoundError: If bucket doesn't exist
    """
    logger.debug("BLL: Uploading file", bucket=bucket, key=key)
    client = get_s3_client()
    return await client.upload_file(bucket, key, file_data, content_type, metadata)


async def delete_file(bucket: str, key: str) -> None:
    """Delete file from S3.

    Removes a file from S3 bucket. This is a write operation
    that modifies S3 state.

    Args:
        bucket: Bucket name
        key: Object key (file path)

    Raises:
        S3DownloadError: If deletion fails
        S3FileNotFoundError: If file doesn't exist
        S3BucketNotFoundError: If bucket doesn't exist
    """
    logger.debug("BLL: Deleting file", bucket=bucket, key=key)
    client = get_s3_client()
    await client.delete_file(bucket, key)


async def generate_presigned_url(
    bucket: str,
    key: str,
    expiration: int = 3600,
    http_method: str = "GET",
) -> str:
    """Generate presigned URL for file access.

    Creates a presigned URL for temporary file access. This is a write operation
    that generates a new access token.

    Args:
        bucket: Bucket name
        key: Object key (file path)
        expiration: URL expiration time in seconds
        http_method: HTTP method (GET or PUT)

    Returns:
        Presigned URL string

    Raises:
        S3DownloadError: If URL generation fails
        S3BucketNotFoundError: If bucket doesn't exist
    """
    logger.debug(
        "BLL: Generating presigned URL",
        bucket=bucket,
        key=key,
        expiration=expiration,
    )
    client = get_s3_client()
    return await client.generate_presigned_url(bucket, key, expiration, http_method)


async def create_multipart_upload(
    bucket: str,
    key: str,
    content_type: str | None = None,
    metadata: MetadataDict | None = None,
) -> MultipartInitResultDict:
    """Initiate multipart upload.

    Creates a new multipart upload session. This is a write operation
    that initializes a multipart upload.

    Args:
        bucket: Bucket name
        key: Object key (file path)
        content_type: Content type (MIME type)
        metadata: Optional metadata dictionary

    Returns:
        Multipart upload initiation result dictionary

    Raises:
        S3MultipartUploadError: If initiation fails
        S3BucketNotFoundError: If bucket doesn't exist
    """
    logger.debug("BLL: Creating multipart upload", bucket=bucket, key=key)
    client = get_s3_client()
    return await client.create_multipart_upload(bucket, key, content_type, metadata)


async def upload_part(
    bucket: str,
    key: str,
    upload_id: str,
    part_number: int,
    part_data: bytes,
) -> MultipartPartResultDict:
    """Upload part in multipart upload.

    Uploads a single part in a multipart upload. This is a write operation
    that adds data to the multipart upload.

    Args:
        bucket: Bucket name
        key: Object key (file path)
        upload_id: Multipart upload ID
        part_number: Part number (1-indexed)
        part_data: Part data as bytes

    Returns:
        Multipart upload part result dictionary

    Raises:
        S3MultipartUploadError: If part upload fails
        S3BucketNotFoundError: If bucket doesn't exist
    """
    logger.debug(
        "BLL: Uploading part",
        bucket=bucket,
        key=key,
        part_number=part_number,
        upload_id=upload_id,
    )
    client = get_s3_client()
    return await client.upload_part(bucket, key, upload_id, part_number, part_data)


async def complete_multipart_upload(
    bucket: str,
    key: str,
    upload_id: str,
    parts: MultipartPartsList,
) -> MultipartCompleteResultDict:
    """Complete multipart upload.

    Completes a multipart upload by combining all parts. This is a write operation
    that finalizes the multipart upload.

    Args:
        bucket: Bucket name
        key: Object key (file path)
        upload_id: Multipart upload ID
        parts: List of parts with ETag and part number

    Returns:
        Multipart upload completion result dictionary

    Raises:
        S3MultipartUploadError: If completion fails
        S3BucketNotFoundError: If bucket doesn't exist
    """
    logger.debug(
        "BLL: Completing multipart upload",
        bucket=bucket,
        key=key,
        upload_id=upload_id,
    )
    client = get_s3_client()
    return await client.complete_multipart_upload(bucket, key, upload_id, parts)


async def abort_multipart_upload(bucket: str, key: str, upload_id: str) -> None:
    """Abort multipart upload.

    Aborts an in-progress multipart upload. This is a write operation
    that cancels the multipart upload.

    Args:
        bucket: Bucket name
        key: Object key (file path)
        upload_id: Multipart upload ID

    Raises:
        S3MultipartUploadError: If abort fails
        S3BucketNotFoundError: If bucket doesn't exist
    """
    logger.debug(
        "BLL: Aborting multipart upload",
        bucket=bucket,
        key=key,
        upload_id=upload_id,
    )
    client = get_s3_client()
    await client.abort_multipart_upload(bucket, key, upload_id)


async def create_bucket(bucket_name: str, region: str | None = None) -> None:
    """Create bucket.

    Creates a new S3 bucket. This is a write operation that creates
    a new bucket resource.

    Args:
        bucket_name: Name of the bucket to create
        region: Optional region (uses default if not provided)

    Raises:
        S3BucketExistsError: If bucket already exists
        S3UploadError: If creation fails
    """
    logger.debug("BLL: Creating bucket", bucket_name=bucket_name, region=region)
    client = get_s3_client()
    await client.create_bucket(bucket_name, region)


async def delete_bucket(bucket_name: str) -> None:
    """Delete bucket.

    Deletes an S3 bucket. This is a write operation that removes
    the bucket resource.

    Args:
        bucket_name: Name of the bucket to delete

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3UploadError: If deletion fails
    """
    logger.debug("BLL: Deleting bucket", bucket_name=bucket_name)
    client = get_s3_client()
    await client.delete_bucket(bucket_name)


async def set_bucket_policy(bucket_name: str, policy: PolicyDict) -> None:
    """Set bucket policy.

    Sets the policy for an S3 bucket. This is a write operation
    that modifies bucket configuration.

    Args:
        bucket_name: Name of the bucket
        policy: Policy dictionary to set

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3UploadError: If setting fails
    """
    logger.debug("BLL: Setting bucket policy", bucket_name=bucket_name)
    client = get_s3_client()
    await client.set_bucket_policy(bucket_name, policy)


async def copy_file(
    source_bucket: str,
    source_key: str,
    destination_bucket: str,
    destination_key: str,
    metadata: MetadataDict | None = None,
) -> dict[str, Any]:
    """Copy file within or between buckets.

    Creates a copy of a file. This is a write operation
    that creates a new object in S3.

    Args:
        source_bucket: Source bucket name
        source_key: Source object key (file path)
        destination_bucket: Destination bucket name
        destination_key: Destination object key (file path)
        metadata: Optional new metadata for copied file

    Returns:
        Dictionary with copy information

    Raises:
        S3UploadError: If copy fails
        S3FileNotFoundError: If source file doesn't exist
        S3BucketNotFoundError: If bucket doesn't exist
    """
    logger.debug(
        "BLL: Copying file",
        source_bucket=source_bucket,
        source_key=source_key,
        destination_bucket=destination_bucket,
        destination_key=destination_key,
    )
    client = get_s3_client()
    return await client.copy_file(
        source_bucket, source_key, destination_bucket, destination_key, metadata
    )


async def move_file(
    source_bucket: str,
    source_key: str,
    destination_bucket: str,
    destination_key: str,
    metadata: MetadataDict | None = None,
) -> dict[str, Any]:
    """Move file within or between buckets.

    Moves a file by copying and then deleting the original.
    This is a write operation that modifies S3 state.

    Args:
        source_bucket: Source bucket name
        source_key: Source object key (file path)
        destination_bucket: Destination bucket name
        destination_key: Destination object key (file path)
        metadata: Optional new metadata for moved file

    Returns:
        Dictionary with move information

    Raises:
        S3UploadError: If move fails
        S3FileNotFoundError: If source file doesn't exist
        S3BucketNotFoundError: If bucket doesn't exist
    """
    logger.debug(
        "BLL: Moving file",
        source_bucket=source_bucket,
        source_key=source_key,
        destination_bucket=destination_bucket,
        destination_key=destination_key,
    )
    client = get_s3_client()

    # Copy file first
    copy_result = await client.copy_file(
        source_bucket, source_key, destination_bucket, destination_key, metadata
    )

    # Delete original file
    try:
        await client.delete_file(source_bucket, source_key)
    except Exception as e:
        # If delete fails, log error but don't fail the move
        # The copy succeeded, so we have the file in the new location
        logger.warning(
            "Failed to delete source file after copy",
            source_bucket=source_bucket,
            source_key=source_key,
            error=str(e),
        )

    return copy_result


async def batch_delete_files(bucket: str, keys: list[str]) -> dict[str, Any]:
    """Delete multiple files in a single request.

    Removes multiple files from S3 bucket. This is a write operation
    that modifies S3 state.

    Args:
        bucket: Bucket name
        keys: List of object keys to delete

    Returns:
        Dictionary with deletion results

    Raises:
        S3DownloadError: If deletion fails
        S3BucketNotFoundError: If bucket doesn't exist
    """
    logger.debug("BLL: Batch deleting files", bucket=bucket, count=len(keys))
    client = get_s3_client()
    return await client.batch_delete_files(bucket, keys)


async def delete_file_version(bucket: str, key: str, version_id: str) -> None:
    """Delete a specific version of a file.

    Removes a specific version of a file. This is a write operation
    that modifies S3 state.

    Args:
        bucket: Bucket name
        key: Object key (file path)
        version_id: Version ID to delete

    Raises:
        S3DownloadError: If deletion fails
        S3FileNotFoundError: If version doesn't exist
        S3BucketNotFoundError: If bucket doesn't exist
    """
    logger.debug(
        "BLL: Deleting file version", bucket=bucket, key=key, version_id=version_id
    )
    client = get_s3_client()
    await client.delete_file_version(bucket, key, version_id)


async def set_bucket_versioning(bucket_name: str, status: str) -> None:
    """Set bucket versioning configuration.

    Enables or suspends versioning on a bucket. This is a write operation
    that modifies bucket configuration.

    Args:
        bucket_name: Name of the bucket
        status: Versioning status ('Enabled' or 'Suspended')

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3UploadError: If setting fails
    """
    logger.debug(
        "BLL: Setting bucket versioning", bucket_name=bucket_name, status=status
    )
    client = get_s3_client()
    await client.set_bucket_versioning(bucket_name, status)


async def set_bucket_lifecycle(bucket_name: str, rules: list[dict[str, Any]]) -> None:
    """Set bucket lifecycle configuration.

    Sets lifecycle rules for a bucket. This is a write operation
    that modifies bucket configuration.

    Args:
        bucket_name: Name of the bucket
        rules: List of lifecycle rules

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3UploadError: If setting fails
    """
    logger.debug("BLL: Setting bucket lifecycle", bucket_name=bucket_name)
    client = get_s3_client()
    await client.set_bucket_lifecycle(bucket_name, rules)


async def set_bucket_cors(bucket_name: str, cors_rules: list[dict[str, Any]]) -> None:
    """Set bucket CORS configuration.

    Sets CORS rules for a bucket. This is a write operation
    that modifies bucket configuration.

    Args:
        bucket_name: Name of the bucket
        cors_rules: List of CORS rules

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3UploadError: If setting fails
    """
    logger.debug("BLL: Setting bucket CORS", bucket_name=bucket_name)
    client = get_s3_client()
    await client.set_bucket_cors(bucket_name, cors_rules)


async def set_bucket_notifications(
    bucket_name: str,
    events: list[str],
    filters: list[dict[str, Any]] | None = None,
    webhook_url: str | None = None,
) -> None:
    """Set bucket notification configuration.

    Sets notification rules for a bucket. This is a write operation
    that modifies bucket configuration.

    Args:
        bucket_name: Name of the bucket
        events: List of S3 events
        filters: Optional filters for notifications
        webhook_url: Optional webhook URL (requires SNS/Lambda setup)

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3UploadError: If setting fails
    """
    logger.debug("BLL: Setting bucket notifications", bucket_name=bucket_name)
    client = get_s3_client()
    await client.set_bucket_notifications(bucket_name, events, filters, webhook_url)
