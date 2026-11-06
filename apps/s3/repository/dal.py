"""Data Access Layer for S3 read operations."""

from typing import Any

from config.logging import get_logger

from ..types import BucketList, FileListDict, FileMetadataDict, PolicyDict
from ..utils.s3_client import get_s3_client

logger = get_logger(__name__)


async def download_file(bucket: str, key: str) -> bytes:
    """Download file from S3.

    Performs a read-only operation to retrieve file data from S3.
    Does not modify any state.

    Args:
        bucket: Bucket name
        key: Object key (file path)

    Returns:
        File data as bytes

    Raises:
        S3DownloadError: If download fails
        S3FileNotFoundError: If file doesn't exist
        S3BucketNotFoundError: If bucket doesn't exist
    """
    logger.debug("DAL: Downloading file", bucket=bucket, key=key)
    client = get_s3_client()
    return await client.download_file(bucket, key)


async def list_files(
    bucket: str,
    prefix: str = "",
    max_keys: int = 1000,
    continuation_token: str | None = None,
) -> FileListDict:
    """List files in bucket with optional prefix.

    Performs a read-only operation to list files in S3 bucket.
    Supports pagination via continuation token.

    Args:
        bucket: Bucket name
        prefix: Prefix to filter files
        max_keys: Maximum number of keys to return
        continuation_token: Token for pagination

    Returns:
        Dictionary with files list and pagination info

    Raises:
        S3DownloadError: If listing fails
        S3BucketNotFoundError: If bucket doesn't exist
    """
    logger.debug("DAL: Listing files", bucket=bucket, prefix=prefix)
    client = get_s3_client()
    return await client.list_files(bucket, prefix, max_keys, continuation_token)


async def get_file_metadata(bucket: str, key: str) -> FileMetadataDict:
    """Get file metadata.

    Performs a read-only operation to retrieve file metadata from S3.
    Does not modify any state.

    Args:
        bucket: Bucket name
        key: Object key (file path)

    Returns:
        Dictionary with file metadata

    Raises:
        S3DownloadError: If metadata retrieval fails
        S3FileNotFoundError: If file doesn't exist
        S3BucketNotFoundError: If bucket doesn't exist
    """
    logger.debug("DAL: Getting file metadata", bucket=bucket, key=key)
    client = get_s3_client()
    return await client.get_file_metadata(bucket, key)


async def list_buckets() -> BucketList:
    """List all buckets.

    Performs a read-only operation to list all S3 buckets.
    Does not modify any state.

    Returns:
        List of bucket dictionaries

    Raises:
        S3DownloadError: If listing fails
    """
    logger.debug("DAL: Listing buckets")
    client = get_s3_client()
    return await client.list_buckets()


async def bucket_exists(bucket_name: str) -> bool:
    """Check if bucket exists.

    Performs a read-only operation to check bucket existence.
    Does not modify any state.

    Args:
        bucket_name: Name of the bucket to check

    Returns:
        True if bucket exists, False otherwise

    Raises:
        S3DownloadError: If check fails
    """
    logger.debug("DAL: Checking bucket existence", bucket_name=bucket_name)
    client = get_s3_client()
    return await client.bucket_exists(bucket_name)


async def get_bucket_policy(bucket_name: str) -> PolicyDict:
    """Get bucket policy.

    Performs a read-only operation to retrieve bucket policy.
    Does not modify any state.

    Args:
        bucket_name: Name of the bucket

    Returns:
        Bucket policy dictionary

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3DownloadError: If retrieval fails
    """
    logger.debug("DAL: Getting bucket policy", bucket_name=bucket_name)
    client = get_s3_client()
    return await client.get_bucket_policy(bucket_name)


async def list_object_versions(bucket: str, key: str) -> dict[str, Any]:
    """List all versions of an object.

    Performs a read-only operation to list object versions.
    Does not modify any state.

    Args:
        bucket: Bucket name
        key: Object key (file path)

    Returns:
        Dictionary with versions list

    Raises:
        S3DownloadError: If listing fails
        S3BucketNotFoundError: If bucket doesn't exist
    """
    logger.debug("DAL: Listing object versions", bucket=bucket, key=key)
    client = get_s3_client()
    return await client.list_object_versions(bucket, key)


async def download_file_version(bucket: str, key: str, version_id: str) -> bytes:
    """Download a specific version of a file.

    Performs a read-only operation to retrieve file version.
    Does not modify any state.

    Args:
        bucket: Bucket name
        key: Object key (file path)
        version_id: Version ID to download

    Returns:
        File data as bytes

    Raises:
        S3DownloadError: If download fails
        S3FileNotFoundError: If version doesn't exist
        S3BucketNotFoundError: If bucket doesn't exist
    """
    logger.debug(
        "DAL: Downloading file version", bucket=bucket, key=key, version_id=version_id
    )
    client = get_s3_client()
    return await client.download_file_version(bucket, key, version_id)


async def get_bucket_versioning(bucket_name: str) -> dict[str, Any]:
    """Get bucket versioning configuration.

    Performs a read-only operation to retrieve versioning config.
    Does not modify any state.

    Args:
        bucket_name: Name of the bucket

    Returns:
        Dictionary with versioning configuration

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3DownloadError: If retrieval fails
    """
    logger.debug("DAL: Getting bucket versioning", bucket_name=bucket_name)
    client = get_s3_client()
    return await client.get_bucket_versioning(bucket_name)


async def get_bucket_lifecycle(bucket_name: str) -> dict[str, Any]:
    """Get bucket lifecycle configuration.

    Performs a read-only operation to retrieve lifecycle config.
    Does not modify any state.

    Args:
        bucket_name: Name of the bucket

    Returns:
        Dictionary with lifecycle configuration

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3DownloadError: If retrieval fails
    """
    logger.debug("DAL: Getting bucket lifecycle", bucket_name=bucket_name)
    client = get_s3_client()
    return await client.get_bucket_lifecycle(bucket_name)


async def get_bucket_cors(bucket_name: str) -> dict[str, Any]:
    """Get bucket CORS configuration.

    Performs a read-only operation to retrieve CORS config.
    Does not modify any state.

    Args:
        bucket_name: Name of the bucket

    Returns:
        Dictionary with CORS configuration

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3DownloadError: If retrieval fails
    """
    logger.debug("DAL: Getting bucket CORS", bucket_name=bucket_name)
    client = get_s3_client()
    return await client.get_bucket_cors(bucket_name)


async def get_bucket_notifications(bucket_name: str) -> dict[str, Any]:
    """Get bucket notification configuration.

    Performs a read-only operation to retrieve notification config.
    Does not modify any state.

    Args:
        bucket_name: Name of the bucket

    Returns:
        Dictionary with notification configuration

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3DownloadError: If retrieval fails
    """
    logger.debug("DAL: Getting bucket notifications", bucket_name=bucket_name)
    client = get_s3_client()
    return await client.get_bucket_notifications(bucket_name)
