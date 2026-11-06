"""Async S3/MinIO client wrapper."""

import io
from typing import Any

import aioboto3
from botocore.exceptions import ClientError, EndpointConnectionError, NoCredentialsError

from config.logging import get_logger
from config.settings import settings

from ..helpers.exceptions import (
    S3BucketExistsError,
    S3BucketNotFoundError,
    S3ConnectionError,
    S3DownloadError,
    S3FileNotFoundError,
    S3MultipartUploadError,
    S3PermissionError,
    S3UploadError,
)

logger = get_logger(__name__)


class S3Client:
    """Async S3 client wrapper for MinIO and AWS S3 operations."""

    def __init__(self) -> None:
        """Initialize S3 client with configuration."""
        if not settings.s3.ENABLED:
            logger.warning("S3 is not enabled in configuration")
            return

        self.endpoint_url = settings.s3.ENDPOINT_URL
        self.access_key_id = settings.s3.ACCESS_KEY_ID
        self.secret_access_key = settings.s3.SECRET_ACCESS_KEY
        self.region = settings.s3.REGION
        self.use_ssl = settings.s3.USE_SSL
        self.default_bucket = settings.s3.BUCKET_NAME

        # Create session
        self.session = aioboto3.Session()

    async def _get_s3_client(self) -> Any:
        """Get S3 client instance.

        Returns:
            S3 client instance

        Raises:
            S3ConnectionError: If connection fails
        """
        try:
            return self.session.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name=self.region,
                use_ssl=self.use_ssl,
            )
        except (NoCredentialsError, EndpointConnectionError) as e:
            logger.error("Failed to create S3 client", error=str(e))
            raise S3ConnectionError(f"Failed to connect to S3: {str(e)}") from e

    async def upload_file(
        self,
        bucket: str,
        key: str,
        file_data: bytes | io.BytesIO,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Upload file to S3.

        Args:
            bucket: Bucket name
            key: Object key (file path)
            file_data: File data as bytes or BytesIO
            content_type: Content type (MIME type)
            metadata: Optional metadata dictionary

        Returns:
            Dictionary with upload information

        Raises:
            S3UploadError: If upload fails
            S3BucketNotFoundError: If bucket doesn't exist
        """
        logger.debug("Uploading file", bucket=bucket, key=key)
        try:
            async with await self._get_s3_client() as s3:
                extra_args: dict[str, Any] = {}
                if content_type:
                    extra_args["ContentType"] = content_type
                if metadata:
                    extra_args["Metadata"] = metadata

                # Convert bytes to BytesIO if needed
                if isinstance(file_data, bytes):
                    file_obj = io.BytesIO(file_data)
                else:
                    file_obj = file_data

                await s3.upload_fileobj(file_obj, bucket, key, ExtraArgs=extra_args)

                logger.info("File uploaded successfully", bucket=bucket, key=key)
                return {
                    "bucket": bucket,
                    "key": key,
                    "content_type": content_type,
                }
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchBucket":
                raise S3BucketNotFoundError(bucket) from e
            if error_code in ("AccessDenied", "Forbidden"):
                raise S3PermissionError(f"Permission denied: {str(e)}") from e
            logger.error("Failed to upload file", error=str(e), bucket=bucket, key=key)
            raise S3UploadError(f"Failed to upload file: {str(e)}") from e
        except Exception as e:
            logger.error(
                "Unexpected error during upload", error=str(e), bucket=bucket, key=key
            )
            raise S3UploadError(f"Unexpected error: {str(e)}") from e

    async def download_file(self, bucket: str, key: str) -> bytes:
        """Download file from S3.

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
        logger.debug("Downloading file", bucket=bucket, key=key)
        try:
            async with await self._get_s3_client() as s3:
                response = await s3.get_object(Bucket=bucket, Key=key)
                file_data = await response["Body"].read()

                logger.info("File downloaded successfully", bucket=bucket, key=key)
                return file_data
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchKey":
                raise S3FileNotFoundError(bucket, key) from e
            if error_code == "NoSuchBucket":
                raise S3BucketNotFoundError(bucket) from e
            if error_code in ("AccessDenied", "Forbidden"):
                raise S3PermissionError(f"Permission denied: {str(e)}") from e
            logger.error(
                "Failed to download file", error=str(e), bucket=bucket, key=key
            )
            raise S3DownloadError(f"Failed to download file: {str(e)}") from e
        except Exception as e:
            logger.error(
                "Unexpected error during download", error=str(e), bucket=bucket, key=key
            )
            raise S3DownloadError(f"Unexpected error: {str(e)}") from e

    async def delete_file(self, bucket: str, key: str) -> None:
        """Delete file from S3.

        Args:
            bucket: Bucket name
            key: Object key (file path)

        Raises:
            S3DownloadError: If deletion fails
            S3FileNotFoundError: If file doesn't exist
            S3BucketNotFoundError: If bucket doesn't exist
        """
        logger.debug("Deleting file", bucket=bucket, key=key)
        try:
            async with await self._get_s3_client() as s3:
                await s3.delete_object(Bucket=bucket, Key=key)
                logger.info("File deleted successfully", bucket=bucket, key=key)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchBucket":
                raise S3BucketNotFoundError(bucket) from e
            if error_code in ("AccessDenied", "Forbidden"):
                raise S3PermissionError(f"Permission denied: {str(e)}") from e
            logger.error("Failed to delete file", error=str(e), bucket=bucket, key=key)
            raise S3DownloadError(f"Failed to delete file: {str(e)}") from e
        except Exception as e:
            logger.error(
                "Unexpected error during deletion", error=str(e), bucket=bucket, key=key
            )
            raise S3DownloadError(f"Unexpected error: {str(e)}") from e

    async def list_files(
        self,
        bucket: str,
        prefix: str = "",
        max_keys: int = 1000,
        continuation_token: str | None = None,
    ) -> dict[str, Any]:
        """List files in bucket with optional prefix.

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
        logger.debug("Listing files", bucket=bucket, prefix=prefix)
        try:
            async with await self._get_s3_client() as s3:
                list_kwargs: dict[str, Any] = {
                    "Bucket": bucket,
                    "MaxKeys": max_keys,
                }
                if prefix:
                    list_kwargs["Prefix"] = prefix
                if continuation_token:
                    list_kwargs["ContinuationToken"] = continuation_token

                response = await s3.list_objects_v2(**list_kwargs)

                files = []
                for obj in response.get("Contents", []):
                    files.append(
                        {
                            "key": obj["Key"],
                            "size": obj["Size"],
                            "last_modified": obj["LastModified"].isoformat(),
                            "etag": obj["ETag"].strip('"'),
                        }
                    )

                result = {
                    "files": files,
                    "is_truncated": response.get("IsTruncated", False),
                    "next_continuation_token": response.get("NextContinuationToken"),
                }

                logger.info(
                    "Files listed successfully", bucket=bucket, count=len(files)
                )
                return result
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchBucket":
                raise S3BucketNotFoundError(bucket) from e
            if error_code in ("AccessDenied", "Forbidden"):
                raise S3PermissionError(f"Permission denied: {str(e)}") from e
            logger.error("Failed to list files", error=str(e), bucket=bucket)
            raise S3DownloadError(f"Failed to list files: {str(e)}") from e
        except Exception as e:
            logger.error("Unexpected error during listing", error=str(e), bucket=bucket)
            raise S3DownloadError(f"Unexpected error: {str(e)}") from e

    async def get_file_metadata(self, bucket: str, key: str) -> dict[str, Any]:
        """Get file metadata.

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
        logger.debug("Getting file metadata", bucket=bucket, key=key)
        try:
            async with await self._get_s3_client() as s3:
                response = await s3.head_object(Bucket=bucket, Key=key)

                metadata = {
                    "key": key,
                    "bucket": bucket,
                    "size": response.get("ContentLength", 0),
                    "content_type": response.get("ContentType", ""),
                    "last_modified": (
                        response.get("LastModified").isoformat()
                        if response.get("LastModified")
                        else None
                    ),
                    "etag": response.get("ETag", "").strip('"'),
                    "metadata": response.get("Metadata", {}),
                }

                logger.info("File metadata retrieved", bucket=bucket, key=key)
                return metadata
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchKey" or error_code == "404":
                raise S3FileNotFoundError(bucket, key) from e
            if error_code == "NoSuchBucket":
                raise S3BucketNotFoundError(bucket) from e
            if error_code in ("AccessDenied", "Forbidden"):
                raise S3PermissionError(f"Permission denied: {str(e)}") from e
            logger.error(
                "Failed to get file metadata", error=str(e), bucket=bucket, key=key
            )
            raise S3DownloadError(f"Failed to get file metadata: {str(e)}") from e
        except Exception as e:
            logger.error(
                "Unexpected error getting metadata",
                error=str(e),
                bucket=bucket,
                key=key,
            )
            raise S3DownloadError(f"Unexpected error: {str(e)}") from e

    async def generate_presigned_url(
        self,
        bucket: str,
        key: str,
        expiration: int = 3600,
        http_method: str = "GET",
    ) -> str:
        """Generate presigned URL for file access.

        Args:
            bucket: Bucket name
            key: Object key (file path)
            expiration: URL expiration time in seconds
            http_method: HTTP method (GET, PUT, etc.)

        Returns:
            Presigned URL string

        Raises:
            S3DownloadError: If URL generation fails
            S3BucketNotFoundError: If bucket doesn't exist
        """
        logger.debug(
            "Generating presigned URL", bucket=bucket, key=key, expiration=expiration
        )
        try:
            async with await self._get_s3_client() as s3:
                url = await s3.generate_presigned_url(
                    "get_object" if http_method == "GET" else "put_object",
                    Params={"Bucket": bucket, "Key": key},
                    ExpiresIn=expiration,
                )

                logger.info("Presigned URL generated", bucket=bucket, key=key)
                return url
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchBucket":
                raise S3BucketNotFoundError(bucket) from e
            if error_code in ("AccessDenied", "Forbidden"):
                raise S3PermissionError(f"Permission denied: {str(e)}") from e
            logger.error(
                "Failed to generate presigned URL", error=str(e), bucket=bucket, key=key
            )
            raise S3DownloadError(f"Failed to generate presigned URL: {str(e)}") from e
        except Exception as e:
            logger.error(
                "Unexpected error generating URL", error=str(e), bucket=bucket, key=key
            )
            raise S3DownloadError(f"Unexpected error: {str(e)}") from e

    async def create_multipart_upload(
        self,
        bucket: str,
        key: str,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Initiate multipart upload.

        Args:
            bucket: Bucket name
            key: Object key (file path)
            content_type: Content type (MIME type)
            metadata: Optional metadata dictionary

        Returns:
            Dictionary with upload_id

        Raises:
            S3MultipartUploadError: If initiation fails
            S3BucketNotFoundError: If bucket doesn't exist
        """
        logger.debug("Initiating multipart upload", bucket=bucket, key=key)
        try:
            async with await self._get_s3_client() as s3:
                init_kwargs: dict[str, Any] = {"Bucket": bucket, "Key": key}
                if content_type:
                    init_kwargs["ContentType"] = content_type
                if metadata:
                    init_kwargs["Metadata"] = metadata

                response = await s3.create_multipart_upload(**init_kwargs)
                upload_id = response["UploadId"]

                logger.info(
                    "Multipart upload initiated",
                    bucket=bucket,
                    key=key,
                    upload_id=upload_id,
                )
                return {
                    "bucket": bucket,
                    "key": key,
                    "upload_id": upload_id,
                }
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchBucket":
                raise S3BucketNotFoundError(bucket) from e
            if error_code in ("AccessDenied", "Forbidden"):
                raise S3PermissionError(f"Permission denied: {str(e)}") from e
            logger.error(
                "Failed to initiate multipart upload",
                error=str(e),
                bucket=bucket,
                key=key,
            )
            raise S3MultipartUploadError(
                f"Failed to initiate multipart upload: {str(e)}"
            ) from e
        except Exception as e:
            logger.error(
                "Unexpected error initiating multipart upload",
                error=str(e),
                bucket=bucket,
                key=key,
            )
            raise S3MultipartUploadError(f"Unexpected error: {str(e)}") from e

    async def upload_part(
        self,
        bucket: str,
        key: str,
        upload_id: str,
        part_number: int,
        part_data: bytes | io.BytesIO,
    ) -> dict[str, Any]:
        """Upload part in multipart upload.

        Args:
            bucket: Bucket name
            key: Object key (file path)
            upload_id: Multipart upload ID
            part_number: Part number (1-indexed)
            part_data: Part data as bytes or BytesIO

        Returns:
            Dictionary with ETag for the part

        Raises:
            S3MultipartUploadError: If part upload fails
        """
        logger.debug(
            "Uploading part",
            bucket=bucket,
            key=key,
            part_number=part_number,
            upload_id=upload_id,
        )
        try:
            async with await self._get_s3_client() as s3:
                # Convert bytes to BytesIO if needed
                if isinstance(part_data, bytes):
                    part_obj = io.BytesIO(part_data)
                else:
                    part_obj = part_data

                response = await s3.upload_part(
                    Bucket=bucket,
                    Key=key,
                    PartNumber=part_number,
                    UploadId=upload_id,
                    Body=part_obj,
                )

                etag = response["ETag"].strip('"')

                logger.info(
                    "Part uploaded",
                    bucket=bucket,
                    key=key,
                    part_number=part_number,
                    etag=etag,
                )
                return {
                    "part_number": part_number,
                    "etag": etag,
                }
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("AccessDenied", "Forbidden"):
                raise S3PermissionError(f"Permission denied: {str(e)}") from e
            logger.error(
                "Failed to upload part",
                error=str(e),
                bucket=bucket,
                key=key,
                part_number=part_number,
            )
            raise S3MultipartUploadError(f"Failed to upload part: {str(e)}") from e
        except Exception as e:
            logger.error(
                "Unexpected error uploading part", error=str(e), bucket=bucket, key=key
            )
            raise S3MultipartUploadError(f"Unexpected error: {str(e)}") from e

    async def complete_multipart_upload(
        self,
        bucket: str,
        key: str,
        upload_id: str,
        parts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Complete multipart upload.

        Args:
            bucket: Bucket name
            key: Object key (file path)
            upload_id: Multipart upload ID
            parts: List of parts with ETag and part number

        Returns:
            Dictionary with completion information

        Raises:
            S3MultipartUploadError: If completion fails
        """
        logger.debug(
            "Completing multipart upload", bucket=bucket, key=key, upload_id=upload_id
        )
        try:
            async with await self._get_s3_client() as s3:
                # Format parts for boto3
                parts_list = [
                    {"ETag": part["etag"], "PartNumber": part["part_number"]}
                    for part in parts
                ]

                response = await s3.complete_multipart_upload(
                    Bucket=bucket,
                    Key=key,
                    UploadId=upload_id,
                    MultipartUpload={"Parts": parts_list},
                )

                logger.info(
                    "Multipart upload completed",
                    bucket=bucket,
                    key=key,
                    upload_id=upload_id,
                )
                return {
                    "bucket": bucket,
                    "key": key,
                    "etag": response.get("ETag", "").strip('"'),
                }
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("AccessDenied", "Forbidden"):
                raise S3PermissionError(f"Permission denied: {str(e)}") from e
            logger.error(
                "Failed to complete multipart upload",
                error=str(e),
                bucket=bucket,
                key=key,
            )
            raise S3MultipartUploadError(
                f"Failed to complete multipart upload: {str(e)}"
            ) from e
        except Exception as e:
            logger.error(
                "Unexpected error completing multipart upload",
                error=str(e),
                bucket=bucket,
                key=key,
            )
            raise S3MultipartUploadError(f"Unexpected error: {str(e)}") from e

    async def abort_multipart_upload(
        self, bucket: str, key: str, upload_id: str
    ) -> None:
        """Abort multipart upload.

        Args:
            bucket: Bucket name
            key: Object key (file path)
            upload_id: Multipart upload ID

        Raises:
            S3MultipartUploadError: If abort fails
        """
        logger.debug(
            "Aborting multipart upload", bucket=bucket, key=key, upload_id=upload_id
        )
        try:
            async with await self._get_s3_client() as s3:
                await s3.abort_multipart_upload(
                    Bucket=bucket, Key=key, UploadId=upload_id
                )
                logger.info(
                    "Multipart upload aborted",
                    bucket=bucket,
                    key=key,
                    upload_id=upload_id,
                )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("AccessDenied", "Forbidden"):
                raise S3PermissionError(f"Permission denied: {str(e)}") from e
            logger.error(
                "Failed to abort multipart upload", error=str(e), bucket=bucket, key=key
            )
            raise S3MultipartUploadError(
                f"Failed to abort multipart upload: {str(e)}"
            ) from e
        except Exception as e:
            logger.error(
                "Unexpected error aborting multipart upload",
                error=str(e),
                bucket=bucket,
                key=key,
            )
            raise S3MultipartUploadError(f"Unexpected error: {str(e)}") from e

    async def create_bucket(self, bucket_name: str, region: str | None = None) -> None:
        """Create bucket.

        Args:
            bucket_name: Name of the bucket to create
            region: Optional region (uses default if not provided)

        Raises:
            S3BucketExistsError: If bucket already exists
            S3UploadError: If creation fails
        """
        logger.debug("Creating bucket", bucket_name=bucket_name)
        try:
            async with await self._get_s3_client() as s3:
                create_kwargs: dict[str, Any] = {"Bucket": bucket_name}
                if region and region != self.region:
                    create_kwargs["CreateBucketConfiguration"] = {
                        "LocationConstraint": region
                    }

                await s3.create_bucket(**create_kwargs)
                logger.info("Bucket created successfully", bucket_name=bucket_name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if (
                error_code == "BucketAlreadyExists"
                or error_code == "BucketAlreadyOwnedByYou"
            ):
                raise S3BucketExistsError(bucket_name) from e
            if error_code in ("AccessDenied", "Forbidden"):
                raise S3PermissionError(f"Permission denied: {str(e)}") from e
            logger.error(
                "Failed to create bucket", error=str(e), bucket_name=bucket_name
            )
            raise S3UploadError(f"Failed to create bucket: {str(e)}") from e
        except Exception as e:
            logger.error(
                "Unexpected error creating bucket",
                error=str(e),
                bucket_name=bucket_name,
            )
            raise S3UploadError(f"Unexpected error: {str(e)}") from e

    async def delete_bucket(self, bucket_name: str) -> None:
        """Delete bucket.

        Args:
            bucket_name: Name of the bucket to delete

        Raises:
            S3BucketNotFoundError: If bucket doesn't exist
            S3UploadError: If deletion fails
        """
        logger.debug("Deleting bucket", bucket_name=bucket_name)
        try:
            async with await self._get_s3_client() as s3:
                await s3.delete_bucket(Bucket=bucket_name)
                logger.info("Bucket deleted successfully", bucket_name=bucket_name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchBucket":
                raise S3BucketNotFoundError(bucket_name) from e
            if error_code in ("AccessDenied", "Forbidden"):
                raise S3PermissionError(f"Permission denied: {str(e)}") from e
            logger.error(
                "Failed to delete bucket", error=str(e), bucket_name=bucket_name
            )
            raise S3UploadError(f"Failed to delete bucket: {str(e)}") from e
        except Exception as e:
            logger.error(
                "Unexpected error deleting bucket",
                error=str(e),
                bucket_name=bucket_name,
            )
            raise S3UploadError(f"Unexpected error: {str(e)}") from e

    async def list_buckets(self) -> list[dict[str, Any]]:
        """List all buckets.

        Returns:
            List of bucket dictionaries

        Raises:
            S3DownloadError: If listing fails
        """
        logger.debug("Listing buckets")
        try:
            async with await self._get_s3_client() as s3:
                response = await s3.list_buckets()

                buckets = []
                for bucket in response.get("Buckets", []):
                    buckets.append(
                        {
                            "name": bucket["Name"],
                            "creation_date": (
                                bucket["CreationDate"].isoformat()
                                if bucket.get("CreationDate")
                                else None
                            ),
                        }
                    )

                logger.info("Buckets listed successfully", count=len(buckets))
                return buckets
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("AccessDenied", "Forbidden"):
                raise S3PermissionError(f"Permission denied: {str(e)}") from e
            logger.error("Failed to list buckets", error=str(e))
            raise S3DownloadError(f"Failed to list buckets: {str(e)}") from e
        except Exception as e:
            logger.error("Unexpected error listing buckets", error=str(e))
            raise S3DownloadError(f"Unexpected error: {str(e)}") from e

    async def bucket_exists(self, bucket_name: str) -> bool:
        """Check if bucket exists.

        Args:
            bucket_name: Name of the bucket to check

        Returns:
            True if bucket exists, False otherwise

        Raises:
            S3DownloadError: If check fails
        """
        logger.debug("Checking bucket existence", bucket_name=bucket_name)
        try:
            async with await self._get_s3_client() as s3:
                await s3.head_bucket(Bucket=bucket_name)
                logger.debug("Bucket exists", bucket_name=bucket_name)
                return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404" or error_code == "NoSuchBucket":
                logger.debug("Bucket does not exist", bucket_name=bucket_name)
                return False
            if error_code in ("AccessDenied", "Forbidden"):
                raise S3PermissionError(f"Permission denied: {str(e)}") from e
            logger.error(
                "Failed to check bucket existence",
                error=str(e),
                bucket_name=bucket_name,
            )
            raise S3DownloadError(f"Failed to check bucket existence: {str(e)}") from e
        except Exception as e:
            logger.error(
                "Unexpected error checking bucket",
                error=str(e),
                bucket_name=bucket_name,
            )
            raise S3DownloadError(f"Unexpected error: {str(e)}") from e

    async def get_bucket_policy(self, bucket_name: str) -> dict[str, Any]:
        """Get bucket policy.

        Args:
            bucket_name: Name of the bucket

        Returns:
            Bucket policy dictionary

        Raises:
            S3BucketNotFoundError: If bucket doesn't exist
            S3DownloadError: If retrieval fails
        """
        logger.debug("Getting bucket policy", bucket_name=bucket_name)
        try:
            async with await self._get_s3_client() as s3:
                response = await s3.get_bucket_policy(Bucket=bucket_name)
                policy = response.get("Policy", "{}")

                import json

                logger.info("Bucket policy retrieved", bucket_name=bucket_name)
                return {"bucket": bucket_name, "policy": json.loads(policy)}
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchBucket":
                raise S3BucketNotFoundError(bucket_name) from e
            if error_code == "NoSuchBucketPolicy":
                return {"bucket": bucket_name, "policy": None}
            if error_code in ("AccessDenied", "Forbidden"):
                raise S3PermissionError(f"Permission denied: {str(e)}") from e
            logger.error(
                "Failed to get bucket policy", error=str(e), bucket_name=bucket_name
            )
            raise S3DownloadError(f"Failed to get bucket policy: {str(e)}") from e
        except Exception as e:
            logger.error(
                "Unexpected error getting bucket policy",
                error=str(e),
                bucket_name=bucket_name,
            )
            raise S3DownloadError(f"Unexpected error: {str(e)}") from e

    async def set_bucket_policy(self, bucket_name: str, policy: dict[str, Any]) -> None:
        """Set bucket policy.

        Args:
            bucket_name: Name of the bucket
            policy: Policy dictionary to set

        Raises:
            S3BucketNotFoundError: If bucket doesn't exist
            S3UploadError: If setting fails
        """
        logger.debug("Setting bucket policy", bucket_name=bucket_name)
        try:
            async with await self._get_s3_client() as s3:
                import json

                policy_json = json.dumps(policy)
                await s3.put_bucket_policy(Bucket=bucket_name, Policy=policy_json)

                logger.info("Bucket policy set", bucket_name=bucket_name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchBucket":
                raise S3BucketNotFoundError(bucket_name) from e
            if error_code in ("AccessDenied", "Forbidden"):
                raise S3PermissionError(f"Permission denied: {str(e)}") from e
            logger.error(
                "Failed to set bucket policy", error=str(e), bucket_name=bucket_name
            )
            raise S3UploadError(f"Failed to set bucket policy: {str(e)}") from e
        except Exception as e:
            logger.error(
                "Unexpected error setting bucket policy",
                error=str(e),
                bucket_name=bucket_name,
            )
            raise S3UploadError(f"Unexpected error: {str(e)}") from e

    async def copy_file(
        self,
        source_bucket: str,
        source_key: str,
        destination_bucket: str,
        destination_key: str,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Copy file within or between buckets.

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
            "Copying file",
            source_bucket=source_bucket,
            source_key=source_key,
            destination_bucket=destination_bucket,
            destination_key=destination_key,
        )
        try:
            async with await self._get_s3_client() as s3:
                copy_source = {"Bucket": source_bucket, "Key": source_key}
                copy_kwargs: dict[str, Any] = {
                    "Bucket": destination_bucket,
                    "CopySource": copy_source,
                    "Key": destination_key,
                }
                if metadata:
                    copy_kwargs["Metadata"] = metadata
                    copy_kwargs["MetadataDirective"] = "REPLACE"

                response = await s3.copy_object(**copy_kwargs)

                logger.info(
                    "File copied successfully",
                    source_bucket=source_bucket,
                    source_key=source_key,
                    destination_bucket=destination_bucket,
                    destination_key=destination_key,
                )
                return {
                    "source_bucket": source_bucket,
                    "source_key": source_key,
                    "destination_bucket": destination_bucket,
                    "destination_key": destination_key,
                    "etag": response.get("CopyObjectResult", {})
                    .get("ETag", "")
                    .strip('"'),
                }
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchKey":
                raise S3FileNotFoundError(source_bucket, source_key) from e
            if error_code == "NoSuchBucket":
                bucket = (
                    destination_bucket
                    if error_code in ("NoSuchBucket", "InvalidBucketName")
                    else source_bucket
                )
                raise S3BucketNotFoundError(bucket) from e
            if error_code in ("AccessDenied", "Forbidden"):
                raise S3PermissionError(f"Permission denied: {str(e)}") from e
            logger.error(
                "Failed to copy file",
                error=str(e),
                source_bucket=source_bucket,
                source_key=source_key,
            )
            raise S3UploadError(f"Failed to copy file: {str(e)}") from e
        except Exception as e:
            logger.error(
                "Unexpected error copying file",
                error=str(e),
                source_bucket=source_bucket,
                source_key=source_key,
            )
            raise S3UploadError(f"Unexpected error: {str(e)}") from e

    async def batch_delete_files(self, bucket: str, keys: list[str]) -> dict[str, Any]:
        """Delete multiple files in a single request.

        Args:
            bucket: Bucket name
            keys: List of object keys to delete

        Returns:
            Dictionary with deletion results

        Raises:
            S3DownloadError: If deletion fails
            S3BucketNotFoundError: If bucket doesn't exist
        """
        logger.debug("Batch deleting files", bucket=bucket, count=len(keys))
        try:
            async with await self._get_s3_client() as s3:
                # S3 allows up to 1000 objects per delete request
                objects = [{"Key": key} for key in keys]

                response = await s3.delete_objects(
                    Bucket=bucket, Delete={"Objects": objects}
                )

                deleted = [obj["Key"] for obj in response.get("Deleted", [])]
                errors = response.get("Errors", [])

                logger.info(
                    "Batch delete completed",
                    bucket=bucket,
                    deleted_count=len(deleted),
                    error_count=len(errors),
                )
                return {
                    "bucket": bucket,
                    "deleted": deleted,
                    "errors": errors,
                }
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchBucket":
                raise S3BucketNotFoundError(bucket) from e
            if error_code in ("AccessDenied", "Forbidden"):
                raise S3PermissionError(f"Permission denied: {str(e)}") from e
            logger.error("Failed to batch delete files", error=str(e), bucket=bucket)
            raise S3DownloadError(f"Failed to batch delete files: {str(e)}") from e
        except Exception as e:
            logger.error(
                "Unexpected error batch deleting files", error=str(e), bucket=bucket
            )
            raise S3DownloadError(f"Unexpected error: {str(e)}") from e

    async def list_object_versions(self, bucket: str, key: str) -> dict[str, Any]:
        """List all versions of an object.

        Args:
            bucket: Bucket name
            key: Object key (file path)

        Returns:
            Dictionary with versions list

        Raises:
            S3DownloadError: If listing fails
            S3BucketNotFoundError: If bucket doesn't exist
        """
        logger.debug("Listing object versions", bucket=bucket, key=key)
        try:
            async with await self._get_s3_client() as s3:
                response = await s3.list_object_versions(
                    Bucket=bucket, Prefix=key, MaxKeys=1000
                )

                versions = []
                for version in response.get("Versions", []):
                    if version["Key"] == key:
                        versions.append(
                            {
                                "version_id": version["VersionId"],
                                "is_latest": version["IsLatest"],
                                "last_modified": version["LastModified"].isoformat(),
                                "size": version["Size"],
                                "etag": version["ETag"].strip('"'),
                            }
                        )

                logger.info(
                    "Object versions listed",
                    bucket=bucket,
                    key=key,
                    version_count=len(versions),
                )
                return {
                    "bucket": bucket,
                    "key": key,
                    "versions": versions,
                }
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchBucket":
                raise S3BucketNotFoundError(bucket) from e
            if error_code in ("AccessDenied", "Forbidden"):
                raise S3PermissionError(f"Permission denied: {str(e)}") from e
            logger.error(
                "Failed to list object versions", error=str(e), bucket=bucket, key=key
            )
            raise S3DownloadError(f"Failed to list object versions: {str(e)}") from e
        except Exception as e:
            logger.error(
                "Unexpected error listing versions",
                error=str(e),
                bucket=bucket,
                key=key,
            )
            raise S3DownloadError(f"Unexpected error: {str(e)}") from e

    async def download_file_version(
        self, bucket: str, key: str, version_id: str
    ) -> bytes:
        """Download a specific version of a file.

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
            "Downloading file version", bucket=bucket, key=key, version_id=version_id
        )
        try:
            async with await self._get_s3_client() as s3:
                response = await s3.get_object(
                    Bucket=bucket, Key=key, VersionId=version_id
                )
                file_data = await response["Body"].read()

                logger.info(
                    "File version downloaded",
                    bucket=bucket,
                    key=key,
                    version_id=version_id,
                )
                return file_data
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchKey" or error_code == "NoSuchVersion":
                raise S3FileNotFoundError(bucket, key) from e
            if error_code == "NoSuchBucket":
                raise S3BucketNotFoundError(bucket) from e
            if error_code in ("AccessDenied", "Forbidden"):
                raise S3PermissionError(f"Permission denied: {str(e)}") from e
            logger.error(
                "Failed to download file version",
                error=str(e),
                bucket=bucket,
                key=key,
                version_id=version_id,
            )
            raise S3DownloadError(f"Failed to download file version: {str(e)}") from e
        except Exception as e:
            logger.error(
                "Unexpected error downloading version",
                error=str(e),
                bucket=bucket,
                key=key,
            )
            raise S3DownloadError(f"Unexpected error: {str(e)}") from e

    async def delete_file_version(self, bucket: str, key: str, version_id: str) -> None:
        """Delete a specific version of a file.

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
            "Deleting file version", bucket=bucket, key=key, version_id=version_id
        )
        try:
            async with await self._get_s3_client() as s3:
                await s3.delete_object(Bucket=bucket, Key=key, VersionId=version_id)
                logger.info(
                    "File version deleted",
                    bucket=bucket,
                    key=key,
                    version_id=version_id,
                )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchBucket":
                raise S3BucketNotFoundError(bucket) from e
            if error_code in ("AccessDenied", "Forbidden"):
                raise S3PermissionError(f"Permission denied: {str(e)}") from e
            logger.error(
                "Failed to delete file version",
                error=str(e),
                bucket=bucket,
                key=key,
                version_id=version_id,
            )
            raise S3DownloadError(f"Failed to delete file version: {str(e)}") from e
        except Exception as e:
            logger.error(
                "Unexpected error deleting version",
                error=str(e),
                bucket=bucket,
                key=key,
            )
            raise S3DownloadError(f"Unexpected error: {str(e)}") from e

    async def get_bucket_versioning(self, bucket_name: str) -> dict[str, Any]:
        """Get bucket versioning configuration.

        Args:
            bucket_name: Name of the bucket

        Returns:
            Dictionary with versioning configuration

        Raises:
            S3BucketNotFoundError: If bucket doesn't exist
            S3DownloadError: If retrieval fails
        """
        logger.debug("Getting bucket versioning", bucket_name=bucket_name)
        try:
            async with await self._get_s3_client() as s3:
                response = await s3.get_bucket_versioning(Bucket=bucket_name)

                status = response.get("Status", "Suspended")
                mfa_delete = response.get("MFADelete")

                logger.info("Bucket versioning retrieved", bucket_name=bucket_name)
                return {
                    "bucket": bucket_name,
                    "status": status,
                    "mfa_delete": mfa_delete,
                }
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchBucket":
                raise S3BucketNotFoundError(bucket_name) from e
            if error_code in ("AccessDenied", "Forbidden"):
                raise S3PermissionError(f"Permission denied: {str(e)}") from e
            logger.error(
                "Failed to get bucket versioning", error=str(e), bucket_name=bucket_name
            )
            raise S3DownloadError(f"Failed to get bucket versioning: {str(e)}") from e
        except Exception as e:
            logger.error(
                "Unexpected error getting versioning",
                error=str(e),
                bucket_name=bucket_name,
            )
            raise S3DownloadError(f"Unexpected error: {str(e)}") from e

    async def set_bucket_versioning(self, bucket_name: str, status: str) -> None:
        """Set bucket versioning configuration.

        Args:
            bucket_name: Name of the bucket
            status: Versioning status ('Enabled' or 'Suspended')

        Raises:
            S3BucketNotFoundError: If bucket doesn't exist
            S3UploadError: If setting fails
        """
        logger.debug(
            "Setting bucket versioning", bucket_name=bucket_name, status=status
        )
        try:
            async with await self._get_s3_client() as s3:
                await s3.put_bucket_versioning(
                    Bucket=bucket_name, VersioningConfiguration={"Status": status}
                )
                logger.info(
                    "Bucket versioning set", bucket_name=bucket_name, status=status
                )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchBucket":
                raise S3BucketNotFoundError(bucket_name) from e
            if error_code in ("AccessDenied", "Forbidden"):
                raise S3PermissionError(f"Permission denied: {str(e)}") from e
            logger.error(
                "Failed to set bucket versioning", error=str(e), bucket_name=bucket_name
            )
            raise S3UploadError(f"Failed to set bucket versioning: {str(e)}") from e
        except Exception as e:
            logger.error(
                "Unexpected error setting versioning",
                error=str(e),
                bucket_name=bucket_name,
            )
            raise S3UploadError(f"Unexpected error: {str(e)}") from e

    async def get_bucket_lifecycle(self, bucket_name: str) -> dict[str, Any]:
        """Get bucket lifecycle configuration.

        Args:
            bucket_name: Name of the bucket

        Returns:
            Dictionary with lifecycle configuration

        Raises:
            S3BucketNotFoundError: If bucket doesn't exist
            S3DownloadError: If retrieval fails
        """
        logger.debug("Getting bucket lifecycle", bucket_name=bucket_name)
        try:
            async with await self._get_s3_client() as s3:
                response = await s3.get_bucket_lifecycle_configuration(
                    Bucket=bucket_name
                )
                rules = response.get("Rules", [])

                logger.info("Bucket lifecycle retrieved", bucket_name=bucket_name)
                return {"bucket": bucket_name, "rules": rules}
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchBucket":
                raise S3BucketNotFoundError(bucket_name) from e
            if error_code == "NoSuchLifecycleConfiguration":
                return {"bucket": bucket_name, "rules": []}
            if error_code in ("AccessDenied", "Forbidden"):
                raise S3PermissionError(f"Permission denied: {str(e)}") from e
            logger.error(
                "Failed to get bucket lifecycle", error=str(e), bucket_name=bucket_name
            )
            raise S3DownloadError(f"Failed to get bucket lifecycle: {str(e)}") from e
        except Exception as e:
            logger.error(
                "Unexpected error getting lifecycle",
                error=str(e),
                bucket_name=bucket_name,
            )
            raise S3DownloadError(f"Unexpected error: {str(e)}") from e

    async def set_bucket_lifecycle(
        self, bucket_name: str, rules: list[dict[str, Any]]
    ) -> None:
        """Set bucket lifecycle configuration.

        Args:
            bucket_name: Name of the bucket
            rules: List of lifecycle rules

        Raises:
            S3BucketNotFoundError: If bucket doesn't exist
            S3UploadError: If setting fails
        """
        logger.debug("Setting bucket lifecycle", bucket_name=bucket_name)
        try:
            async with await self._get_s3_client() as s3:
                await s3.put_bucket_lifecycle_configuration(
                    Bucket=bucket_name, LifecycleConfiguration={"Rules": rules}
                )
                logger.info("Bucket lifecycle set", bucket_name=bucket_name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchBucket":
                raise S3BucketNotFoundError(bucket_name) from e
            if error_code in ("AccessDenied", "Forbidden"):
                raise S3PermissionError(f"Permission denied: {str(e)}") from e
            logger.error(
                "Failed to set bucket lifecycle", error=str(e), bucket_name=bucket_name
            )
            raise S3UploadError(f"Failed to set bucket lifecycle: {str(e)}") from e
        except Exception as e:
            logger.error(
                "Unexpected error setting lifecycle",
                error=str(e),
                bucket_name=bucket_name,
            )
            raise S3UploadError(f"Unexpected error: {str(e)}") from e

    async def get_bucket_cors(self, bucket_name: str) -> dict[str, Any]:
        """Get bucket CORS configuration.

        Args:
            bucket_name: Name of the bucket

        Returns:
            Dictionary with CORS configuration

        Raises:
            S3BucketNotFoundError: If bucket doesn't exist
            S3DownloadError: If retrieval fails
        """
        logger.debug("Getting bucket CORS", bucket_name=bucket_name)
        try:
            async with await self._get_s3_client() as s3:
                response = await s3.get_bucket_cors(Bucket=bucket_name)
                cors_rules = response.get("CORSRules", [])

                logger.info("Bucket CORS retrieved", bucket_name=bucket_name)
                return {"bucket": bucket_name, "cors_rules": cors_rules}
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchBucket":
                raise S3BucketNotFoundError(bucket_name) from e
            if error_code == "NoSuchCORSConfiguration":
                return {"bucket": bucket_name, "cors_rules": []}
            if error_code in ("AccessDenied", "Forbidden"):
                raise S3PermissionError(f"Permission denied: {str(e)}") from e
            logger.error(
                "Failed to get bucket CORS", error=str(e), bucket_name=bucket_name
            )
            raise S3DownloadError(f"Failed to get bucket CORS: {str(e)}") from e
        except Exception as e:
            logger.error(
                "Unexpected error getting CORS", error=str(e), bucket_name=bucket_name
            )
            raise S3DownloadError(f"Unexpected error: {str(e)}") from e

    async def set_bucket_cors(
        self, bucket_name: str, cors_rules: list[dict[str, Any]]
    ) -> None:
        """Set bucket CORS configuration.

        Args:
            bucket_name: Name of the bucket
            cors_rules: List of CORS rules

        Raises:
            S3BucketNotFoundError: If bucket doesn't exist
            S3UploadError: If setting fails
        """
        logger.debug("Setting bucket CORS", bucket_name=bucket_name)
        try:
            async with await self._get_s3_client() as s3:
                await s3.put_bucket_cors(
                    Bucket=bucket_name, CORSConfiguration={"CORSRules": cors_rules}
                )
                logger.info("Bucket CORS set", bucket_name=bucket_name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchBucket":
                raise S3BucketNotFoundError(bucket_name) from e
            if error_code in ("AccessDenied", "Forbidden"):
                raise S3PermissionError(f"Permission denied: {str(e)}") from e
            logger.error(
                "Failed to set bucket CORS", error=str(e), bucket_name=bucket_name
            )
            raise S3UploadError(f"Failed to set bucket CORS: {str(e)}") from e
        except Exception as e:
            logger.error(
                "Unexpected error setting CORS", error=str(e), bucket_name=bucket_name
            )
            raise S3UploadError(f"Unexpected error: {str(e)}") from e

    async def get_bucket_notifications(self, bucket_name: str) -> dict[str, Any]:
        """Get bucket notification configuration.

        Args:
            bucket_name: Name of the bucket

        Returns:
            Dictionary with notification configuration

        Raises:
            S3BucketNotFoundError: If bucket doesn't exist
            S3DownloadError: If retrieval fails
        """
        logger.debug("Getting bucket notifications", bucket_name=bucket_name)
        try:
            async with await self._get_s3_client() as s3:
                response = await s3.get_bucket_notification_configuration(
                    Bucket=bucket_name
                )

                notifications = []
                # S3 supports SQS, SNS, and Lambda notifications
                # For webhooks, we'll store in a custom format
                if "QueueConfigurations" in response:
                    for queue in response["QueueConfigurations"]:
                        notifications.append(
                            {
                                "type": "sqs",
                                "queue_arn": queue.get("QueueArn"),
                                "events": queue.get("Events", []),
                                "filters": queue.get("Filter", {}),
                            }
                        )
                if "TopicConfigurations" in response:
                    for topic in response["TopicConfigurations"]:
                        notifications.append(
                            {
                                "type": "sns",
                                "topic_arn": topic.get("TopicArn"),
                                "events": topic.get("Events", []),
                                "filters": topic.get("Filter", {}),
                            }
                        )
                if "LambdaFunctionConfigurations" in response:
                    for func in response["LambdaFunctionConfigurations"]:
                        notifications.append(
                            {
                                "type": "lambda",
                                "lambda_arn": func.get("LambdaFunctionArn"),
                                "events": func.get("Events", []),
                                "filters": func.get("Filter", {}),
                            }
                        )

                logger.info("Bucket notifications retrieved", bucket_name=bucket_name)
                return {"bucket": bucket_name, "notifications": notifications}
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchBucket":
                raise S3BucketNotFoundError(bucket_name) from e
            if error_code in ("AccessDenied", "Forbidden"):
                raise S3PermissionError(f"Permission denied: {str(e)}") from e
            logger.error(
                "Failed to get bucket notifications",
                error=str(e),
                bucket_name=bucket_name,
            )
            raise S3DownloadError(
                f"Failed to get bucket notifications: {str(e)}"
            ) from e
        except Exception as e:
            logger.error(
                "Unexpected error getting notifications",
                error=str(e),
                bucket_name=bucket_name,
            )
            raise S3DownloadError(f"Unexpected error: {str(e)}") from e

    async def set_bucket_notifications(
        self,
        bucket_name: str,
        events: list[str],
        filters: list[dict[str, Any]] | None = None,
        webhook_url: str | None = None,
    ) -> None:
        """Set bucket notification configuration.

        Note: S3 native notifications support SQS, SNS, and Lambda.
        For webhooks, you would typically use SNS to trigger a Lambda
        that sends HTTP requests. This is a simplified interface.

        Args:
            bucket_name: Name of the bucket
            events: List of S3 events (e.g., 's3:ObjectCreated:*')
            filters: Optional filters for notifications
            webhook_url: Optional webhook URL (requires SNS/Lambda setup)

        Raises:
            S3BucketNotFoundError: If bucket doesn't exist
            S3UploadError: If setting fails
        """
        logger.debug("Setting bucket notifications", bucket_name=bucket_name)
        try:
            async with await self._get_s3_client() as s3:
                # For webhook support, you'd need to set up SNS topic
                # and Lambda function. This is a placeholder implementation.
                # In production, you'd configure SNS -> Lambda -> Webhook

                notification_config: dict[str, Any] = {}

                # If webhook_url is provided, note that S3 doesn't directly
                # support webhooks. You need SNS + Lambda setup.
                # This is a simplified interface that would require
                # additional infrastructure setup.

                # For now, we'll just validate the configuration
                # In a real implementation, you'd create SNS topic and Lambda
                if webhook_url:
                    logger.warning(
                        "Webhook notifications require SNS/Lambda setup",
                        bucket_name=bucket_name,
                        webhook_url=webhook_url,
                    )
                    # This would require additional AWS resources
                    # For now, we'll raise an error indicating setup needed
                    raise S3UploadError(
                        "Webhook notifications require SNS topic and Lambda function setup. "
                        "Please configure these resources separately."
                    )

                # For SQS/SNS/Lambda, you'd configure here
                # This is a placeholder - actual implementation requires
                # ARNs for SQS queues, SNS topics, or Lambda functions

                await s3.put_bucket_notification_configuration(
                    Bucket=bucket_name,
                    NotificationConfiguration=notification_config,
                )
                logger.info("Bucket notifications set", bucket_name=bucket_name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchBucket":
                raise S3BucketNotFoundError(bucket_name) from e
            if error_code in ("AccessDenied", "Forbidden"):
                raise S3PermissionError(f"Permission denied: {str(e)}") from e
            logger.error(
                "Failed to set bucket notifications",
                error=str(e),
                bucket_name=bucket_name,
            )
            raise S3UploadError(f"Failed to set bucket notifications: {str(e)}") from e
        except Exception as e:
            logger.error(
                "Unexpected error setting notifications",
                error=str(e),
                bucket_name=bucket_name,
            )
            raise S3UploadError(f"Unexpected error: {str(e)}") from e


# Global client instance
_client_instance: S3Client | None = None


def get_s3_client() -> S3Client:
    """Get global S3 client instance.

    Returns:
        Global S3Client instance
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = S3Client()
    return _client_instance
