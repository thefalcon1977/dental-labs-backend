"""Router definitions for S3 endpoints."""

from fastapi import APIRouter, Depends, Query, UploadFile, status
from fastapi.responses import ORJSONResponse, StreamingResponse

from apps.auth.dependencies import UserInfo, get_current_user
from apps.core.utils.security import validate_s3_bucket_name, validate_s3_key
from config.logging import get_logger
from config.settings import settings

from .. import schemas, services

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/files/upload",
    response_model=schemas.FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload file",
    description="Upload a file to S3/MinIO",
)
async def upload_file(
    bucket: str = Query(..., description="Bucket name"),
    key: str = Query(..., description="File key (path)"),
    file: UploadFile = ...,
    current_user: UserInfo = Depends(get_current_user),
) -> schemas.FileUploadResponse:
    """Upload file to S3/MinIO.

    Uploads a file to the specified S3/MinIO bucket and key.
    Validates file size against configured maximum upload size.

    Args:
        bucket: Bucket name where file will be stored
        key: File key (path) within the bucket
        file: Upload file object containing file data
        current_user: Current authenticated user (injected via dependency)

    Returns:
        File upload response with bucket, key, and content type

    Raises:
        ValidationError: If file size exceeds maximum allowed size
        S3UploadError: If upload fails
        S3BucketNotFoundError: If bucket doesn't exist
    """
    # Validate bucket and key to prevent path traversal
    bucket = validate_s3_bucket_name(bucket)
    key = validate_s3_key(key)

    logger.debug("Uploading file", bucket=bucket, key=key, user_id=current_user.id)

    # Read file data
    file_data = await file.read()

    # Check file size
    max_size = settings.s3.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(file_data) > max_size:
        from apps.core.exceptions import ValidationError

        raise ValidationError(
            f"File size exceeds maximum allowed size of {settings.s3.MAX_UPLOAD_SIZE_MB}MB"
        )

    result = await services.upload_file(
        bucket=bucket,
        key=key,
        file_data=file_data,
        content_type=file.content_type,
    )

    logger.info("File uploaded", bucket=bucket, key=key, user_id=current_user.id)
    return result


@router.get(
    "/files/download/{bucket}/{key:path}",
    status_code=status.HTTP_200_OK,
    summary="Download file",
    description="Download a file from S3/MinIO",
)
async def download_file(
    bucket: str,
    key: str,
    current_user: UserInfo = Depends(get_current_user),
) -> StreamingResponse:
    """Download file from S3/MinIO.

    Downloads a file from the specified S3/MinIO bucket and key.
    Returns file as a streaming response with appropriate content type.

    Args:
        bucket: Bucket name containing the file
        key: File key (path) within the bucket
        current_user: Current authenticated user (injected via dependency)

    Returns:
        Streaming response with file data and content type

    Raises:
        S3FileNotFoundError: If file doesn't exist
        S3BucketNotFoundError: If bucket doesn't exist
        S3DownloadError: If download fails
    """
    # Validate bucket and key to prevent path traversal
    bucket = validate_s3_bucket_name(bucket)
    key = validate_s3_key(key)

    logger.debug("Downloading file", bucket=bucket, key=key, user_id=current_user.id)

    file_data, content_type = await services.download_file(bucket, key)

    logger.info("File downloaded", bucket=bucket, key=key, user_id=current_user.id)

    return StreamingResponse(
        iter([file_data]),
        media_type=content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{key.split("/")[-1]}"',
        },
    )


@router.delete(
    "/files/{bucket}/{key:path}",
    status_code=status.HTTP_200_OK,
    summary="Delete file",
    description="Delete a file from S3/MinIO",
)
async def delete_file(
    bucket: str,
    key: str,
    current_user: UserInfo = Depends(get_current_user),
) -> ORJSONResponse:
    """Delete file from S3/MinIO.

    Deletes a file from the specified S3/MinIO bucket and key.

    Args:
        bucket: Bucket name containing the file
        key: File key (path) within the bucket
        current_user: Current authenticated user (injected via dependency)

    Returns:
        JSON response confirming deletion

    Raises:
        S3FileNotFoundError: If file doesn't exist
        S3BucketNotFoundError: If bucket doesn't exist
        S3DownloadError: If deletion fails
    """
    # Validate bucket and key to prevent path traversal
    bucket = validate_s3_bucket_name(bucket)
    key = validate_s3_key(key)

    logger.debug("Deleting file", bucket=bucket, key=key, user_id=current_user.id)

    await services.delete_file(bucket, key)

    logger.info("File deleted", bucket=bucket, key=key, user_id=current_user.id)

    return ORJSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "File deleted successfully", "bucket": bucket, "key": key},
    )


@router.get(
    "/files/list",
    response_model=schemas.FileListResponse,
    status_code=status.HTTP_200_OK,
    summary="List files",
    description="List files in a bucket with optional prefix and pagination",
)
async def list_files(
    bucket: str = Query(..., description="Bucket name"),
    prefix: str = Query("", description="Prefix to filter files"),
    max_keys: int = Query(
        1000, ge=1, le=10000, description="Maximum number of keys to return"
    ),
    continuation_token: str | None = Query(None, description="Token for pagination"),
    current_user: UserInfo = Depends(get_current_user),
) -> schemas.FileListResponse:
    """List files in S3/MinIO bucket.

    Lists files in the specified bucket with optional prefix filtering
    and pagination support.

    Args:
        bucket: Bucket name to list files from
        prefix: Optional prefix to filter files by key prefix
        max_keys: Maximum number of keys to return (1-10000)
        continuation_token: Optional token for pagination (from previous response)
        current_user: Current authenticated user (injected via dependency)

    Returns:
        File list response with files, pagination info, and continuation token

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3DownloadError: If listing fails
    """
    # Validate bucket to prevent path traversal
    bucket = validate_s3_bucket_name(bucket)
    # Validate prefix if provided
    if prefix:
        prefix = validate_s3_key(prefix)

    logger.debug("Listing files", bucket=bucket, prefix=prefix, user_id=current_user.id)

    result = await services.list_files(bucket, prefix, max_keys, continuation_token)

    logger.info(
        "Files listed", bucket=bucket, count=len(result.files), user_id=current_user.id
    )
    return result


@router.get(
    "/files/metadata/{bucket}/{key:path}",
    response_model=schemas.FileMetadataResponse,
    status_code=status.HTTP_200_OK,
    summary="Get file metadata",
    description="Get metadata for a file in S3/MinIO",
)
async def get_file_metadata(
    bucket: str,
    key: str,
    current_user: UserInfo = Depends(get_current_user),
) -> schemas.FileMetadataResponse:
    """Get file metadata from S3/MinIO.

    Retrieves metadata for a file in the specified bucket and key,
    including size, content type, last modified date, and ETag.

    Args:
        bucket: Bucket name containing the file
        key: File key (path) within the bucket
        current_user: Current authenticated user (injected via dependency)

    Returns:
        File metadata response with file information

    Raises:
        S3FileNotFoundError: If file doesn't exist
        S3BucketNotFoundError: If bucket doesn't exist
        S3DownloadError: If metadata retrieval fails
    """
    # Validate bucket and key to prevent path traversal
    bucket = validate_s3_bucket_name(bucket)
    key = validate_s3_key(key)

    logger.debug(
        "Getting file metadata", bucket=bucket, key=key, user_id=current_user.id
    )

    result = await services.get_file_metadata(bucket, key)

    logger.info(
        "File metadata retrieved", bucket=bucket, key=key, user_id=current_user.id
    )
    return result


@router.post(
    "/files/presigned-url",
    response_model=schemas.PresignedUrlResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate presigned URL",
    description="Generate a presigned URL for file access",
)
async def generate_presigned_url(
    request: schemas.PresignedUrlRequest,
    current_user: UserInfo = Depends(get_current_user),
) -> schemas.PresignedUrlResponse:
    """Generate presigned URL for file access.

    Generates a presigned URL that allows temporary access to a file
    without authentication. URL expires after specified time.

    Args:
        request: Presigned URL request with bucket, key, expiration, and HTTP method
        current_user: Current authenticated user (injected via dependency)

    Returns:
        Presigned URL response with URL, bucket, key, and expiration

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3DownloadError: If URL generation fails
    """
    # Validate bucket and key to prevent path traversal
    bucket = validate_s3_bucket_name(request.bucket)
    key = validate_s3_key(request.key)

    logger.debug(
        "Generating presigned URL",
        bucket=bucket,
        key=key,
        user_id=current_user.id,
    )

    # Use configured expiry if not provided
    expiration = request.expiration or settings.s3.PRESIGNED_URL_EXPIRY

    result = await services.generate_presigned_url(
        bucket=bucket,
        key=key,
        expiration=expiration,
        http_method=request.http_method,
    )

    logger.info(
        "Presigned URL generated",
        bucket=bucket,
        key=key,
        user_id=current_user.id,
    )
    return result


@router.post(
    "/files/multipart/init",
    response_model=schemas.MultipartUploadInitResponse,
    status_code=status.HTTP_200_OK,
    summary="Initiate multipart upload",
    description="Initiate a multipart upload for large files",
)
async def initiate_multipart_upload(
    request: schemas.MultipartUploadInitRequest,
    current_user: UserInfo = Depends(get_current_user),
) -> schemas.MultipartUploadInitResponse:
    """Initiate multipart upload for large files.

    Initiates a multipart upload session for uploading large files
    in multiple parts. Returns upload ID for subsequent part uploads.

    Args:
        request: Multipart upload initiation request with bucket, key, content type, and metadata
        current_user: Current authenticated user (injected via dependency)

    Returns:
        Multipart upload initiation response with upload ID

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3MultipartUploadError: If initiation fails
    """
    # Validate bucket and key to prevent path traversal
    bucket = validate_s3_bucket_name(request.bucket)
    key = validate_s3_key(request.key)

    logger.debug(
        "Initiating multipart upload",
        bucket=bucket,
        key=key,
        user_id=current_user.id,
    )

    result = await services.initiate_multipart_upload(
        bucket=bucket,
        key=key,
        content_type=request.content_type,
        metadata=request.metadata,
    )

    logger.info(
        "Multipart upload initiated",
        bucket=bucket,
        key=key,
        upload_id=result.upload_id,
        user_id=current_user.id,
    )
    return result


@router.post(
    "/files/multipart/upload",
    response_model=schemas.MultipartUploadPartResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload part",
    description="Upload a part in a multipart upload",
)
async def upload_part(
    bucket: str = Query(..., description="Bucket name"),
    key: str = Query(..., description="File key (path)"),
    upload_id: str = Query(..., description="Multipart upload ID"),
    part_number: int = Query(..., ge=1, le=10000, description="Part number (1-10000)"),
    file: UploadFile = ...,
    current_user: UserInfo = Depends(get_current_user),
) -> schemas.MultipartUploadPartResponse:
    """Upload a part in multipart upload.

    Uploads a single part of a multipart upload. Parts must be uploaded
    in order and then completed using the complete endpoint.

    Args:
        bucket: Bucket name for the multipart upload
        key: File key (path) for the multipart upload
        upload_id: Multipart upload ID from initiation
        part_number: Part number (1-10000, must be sequential)
        file: Upload file object containing part data
        current_user: Current authenticated user (injected via dependency)

    Returns:
        Multipart upload part response with ETag and part number

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3MultipartUploadError: If part upload fails
    """
    # Validate bucket and key to prevent path traversal
    bucket = validate_s3_bucket_name(bucket)
    key = validate_s3_key(key)

    logger.debug(
        "Uploading part",
        bucket=bucket,
        key=key,
        part_number=part_number,
        upload_id=upload_id,
        user_id=current_user.id,
    )

    part_data = await file.read()

    result = await services.upload_part(
        bucket=bucket,
        key=key,
        upload_id=upload_id,
        part_number=part_number,
        part_data=part_data,
    )

    logger.info(
        "Part uploaded",
        bucket=bucket,
        key=key,
        part_number=part_number,
        user_id=current_user.id,
    )
    return result


@router.post(
    "/files/multipart/complete",
    response_model=schemas.MultipartUploadCompleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete multipart upload",
    description="Complete a multipart upload",
)
async def complete_multipart_upload(
    request: schemas.MultipartUploadCompleteRequest,
    current_user: UserInfo = Depends(get_current_user),
) -> schemas.MultipartUploadCompleteResponse:
    """Complete multipart upload.

    Completes a multipart upload by combining all uploaded parts
    into a single file. All parts must be uploaded before completion.

    Args:
        request: Multipart upload completion request with bucket, key, upload ID, and parts list
        current_user: Current authenticated user (injected via dependency)

    Returns:
        Multipart upload completion response with file information

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3MultipartUploadError: If completion fails
    """
    # Validate bucket and key to prevent path traversal
    bucket = validate_s3_bucket_name(request.bucket)
    key = validate_s3_key(request.key)

    logger.debug(
        "Completing multipart upload",
        bucket=bucket,
        key=key,
        upload_id=request.upload_id,
        user_id=current_user.id,
    )

    result = await services.complete_multipart_upload(
        bucket=bucket,
        key=key,
        upload_id=request.upload_id,
        parts=request.parts,
    )

    logger.info(
        "Multipart upload completed",
        bucket=bucket,
        key=key,
        user_id=current_user.id,
    )
    return result


@router.post(
    "/files/multipart/abort",
    status_code=status.HTTP_200_OK,
    summary="Abort multipart upload",
    description="Abort a multipart upload",
)
async def abort_multipart_upload(
    bucket: str = Query(..., description="Bucket name"),
    key: str = Query(..., description="File key (path)"),
    upload_id: str = Query(..., description="Multipart upload ID"),
    current_user: UserInfo = Depends(get_current_user),
) -> ORJSONResponse:
    """Abort multipart upload.

    Aborts an in-progress multipart upload, cleaning up all uploaded parts.
    Cannot be undone once aborted.

    Args:
        bucket: Bucket name for the multipart upload
        key: File key (path) for the multipart upload
        upload_id: Multipart upload ID to abort
        current_user: Current authenticated user (injected via dependency)

    Returns:
        JSON response confirming abort

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3MultipartUploadError: If abort fails
    """
    # Validate bucket and key to prevent path traversal
    bucket = validate_s3_bucket_name(bucket)
    key = validate_s3_key(key)

    logger.debug(
        "Aborting multipart upload",
        bucket=bucket,
        key=key,
        upload_id=upload_id,
        user_id=current_user.id,
    )

    await services.abort_multipart_upload(bucket, key, upload_id)

    logger.info(
        "Multipart upload aborted", bucket=bucket, key=key, user_id=current_user.id
    )

    return ORJSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Multipart upload aborted successfully"},
    )


@router.post(
    "/buckets",
    response_model=schemas.BucketCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create bucket",
    description="Create a new S3/MinIO bucket",
)
async def create_bucket(
    request: schemas.BucketCreateRequest,
    current_user: UserInfo = Depends(get_current_user),
) -> schemas.BucketCreateResponse:
    """Create a new S3/MinIO bucket.

    Creates a new bucket with the specified name and optional region.
    Bucket names must be globally unique within the S3 service.

    Args:
        request: Bucket creation request with bucket name and optional region
        current_user: Current authenticated user (injected via dependency)

    Returns:
        Bucket creation response with bucket name and success message

    Raises:
        S3BucketExistsError: If bucket already exists
        S3UploadError: If creation fails
    """
    # Validate bucket name to prevent path traversal
    bucket_name = validate_s3_bucket_name(request.bucket_name)

    logger.debug("Creating bucket", bucket_name=bucket_name, user_id=current_user.id)

    result = await services.create_bucket(bucket_name, request.region)

    logger.info("Bucket created", bucket_name=bucket_name, user_id=current_user.id)
    return result


@router.delete(
    "/buckets/{bucket_name}",
    status_code=status.HTTP_200_OK,
    summary="Delete bucket",
    description="Delete an S3/MinIO bucket",
)
async def delete_bucket(
    bucket_name: str,
    current_user: UserInfo = Depends(get_current_user),
) -> ORJSONResponse:
    """Delete an S3/MinIO bucket.

    Deletes the specified bucket. Bucket must be empty before deletion.

    Args:
        bucket_name: Name of the bucket to delete
        current_user: Current authenticated user (injected via dependency)

    Returns:
        JSON response confirming deletion

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3UploadError: If deletion fails (e.g., bucket not empty)
    """
    # Validate bucket name to prevent path traversal
    bucket_name = validate_s3_bucket_name(bucket_name)

    logger.debug("Deleting bucket", bucket_name=bucket_name, user_id=current_user.id)

    await services.delete_bucket(bucket_name)

    logger.info("Bucket deleted", bucket_name=bucket_name, user_id=current_user.id)

    return ORJSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": f"Bucket '{bucket_name}' deleted successfully"},
    )


@router.get(
    "/buckets",
    response_model=schemas.BucketListResponse,
    status_code=status.HTTP_200_OK,
    summary="List buckets",
    description="List all S3/MinIO buckets",
)
async def list_buckets(
    current_user: UserInfo = Depends(get_current_user),
) -> schemas.BucketListResponse:
    """List all S3/MinIO buckets.

    Retrieves a list of all buckets accessible by the current user.

    Args:
        current_user: Current authenticated user (injected via dependency)

    Returns:
        Bucket list response with all accessible buckets

    Raises:
        S3DownloadError: If listing fails
    """
    logger.debug("Listing buckets", user_id=current_user.id)

    result = await services.list_buckets()

    logger.info("Buckets listed", count=len(result.buckets), user_id=current_user.id)
    return result


@router.get(
    "/buckets/{bucket_name}/exists",
    status_code=status.HTTP_200_OK,
    summary="Check bucket exists",
    description="Check if a bucket exists",
)
async def bucket_exists(
    bucket_name: str,
    current_user: UserInfo = Depends(get_current_user),
) -> ORJSONResponse:
    """Check if bucket exists.

    Checks whether the specified bucket exists and is accessible.

    Args:
        bucket_name: Name of the bucket to check
        current_user: Current authenticated user (injected via dependency)

    Returns:
        JSON response with bucket name and existence status

    Raises:
        S3DownloadError: If check fails
    """
    # Validate bucket name to prevent path traversal
    bucket_name = validate_s3_bucket_name(bucket_name)

    logger.debug(
        "Checking bucket existence", bucket_name=bucket_name, user_id=current_user.id
    )

    exists = await services.bucket_exists(bucket_name)

    return ORJSONResponse(
        status_code=status.HTTP_200_OK,
        content={"bucket": bucket_name, "exists": exists},
    )


@router.get(
    "/buckets/{bucket_name}/policy",
    response_model=schemas.BucketPolicyResponse,
    status_code=status.HTTP_200_OK,
    summary="Get bucket policy",
    description="Get the policy for a bucket",
)
async def get_bucket_policy(
    bucket_name: str,
    current_user: UserInfo = Depends(get_current_user),
) -> schemas.BucketPolicyResponse:
    """Get bucket policy.

    Retrieves the access policy for the specified bucket.

    Args:
        bucket_name: Name of the bucket
        current_user: Current authenticated user (injected via dependency)

    Returns:
        Bucket policy response with policy document

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3DownloadError: If retrieval fails
    """
    # Validate bucket name to prevent path traversal
    bucket_name = validate_s3_bucket_name(bucket_name)

    logger.debug(
        "Getting bucket policy", bucket_name=bucket_name, user_id=current_user.id
    )

    result = await services.get_bucket_policy(bucket_name)

    logger.info(
        "Bucket policy retrieved", bucket_name=bucket_name, user_id=current_user.id
    )
    return result


@router.put(
    "/buckets/{bucket_name}/policy",
    status_code=status.HTTP_200_OK,
    summary="Set bucket policy",
    description="Set the policy for a bucket",
)
async def set_bucket_policy(
    bucket_name: str,
    request: schemas.BucketPolicyRequest,
    current_user: UserInfo = Depends(get_current_user),
) -> ORJSONResponse:
    """Set bucket policy.

    Sets or updates the access policy for the specified bucket.
    Policy must be a valid JSON policy document.

    Args:
        bucket_name: Name of the bucket
        request: Bucket policy request with policy document
        current_user: Current authenticated user (injected via dependency)

    Returns:
        JSON response confirming policy update

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3UploadError: If setting fails (e.g., invalid policy)
    """
    # Validate bucket name to prevent path traversal
    bucket_name = validate_s3_bucket_name(bucket_name)

    logger.debug(
        "Setting bucket policy", bucket_name=bucket_name, user_id=current_user.id
    )

    await services.set_bucket_policy(bucket_name, request.policy)

    logger.info("Bucket policy set", bucket_name=bucket_name, user_id=current_user.id)

    return ORJSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": f"Policy set for bucket '{bucket_name}'"},
    )


@router.post(
    "/files/copy",
    response_model=schemas.FileCopyResponse,
    status_code=status.HTTP_200_OK,
    summary="Copy file",
    description="Copy a file within or between buckets",
)
async def copy_file(
    request: schemas.FileCopyRequest,
    current_user: UserInfo = Depends(get_current_user),
) -> schemas.FileCopyResponse:
    """Copy file within or between buckets.

    Creates a copy of a file in the specified destination bucket and key.
    The original file remains unchanged.

    Args:
        request: File copy request with source and destination information
        current_user: Current authenticated user (injected via dependency)

    Returns:
        File copy response with source and destination information

    Raises:
        S3FileNotFoundError: If source file doesn't exist
        S3BucketNotFoundError: If bucket doesn't exist
        S3UploadError: If copy fails
    """
    # Validate all bucket and key parameters to prevent path traversal
    source_bucket = validate_s3_bucket_name(request.source_bucket)
    source_key = validate_s3_key(request.source_key)
    destination_bucket = validate_s3_bucket_name(request.destination_bucket)
    destination_key = validate_s3_key(request.destination_key)

    logger.debug(
        "Copying file",
        source_bucket=source_bucket,
        source_key=source_key,
        destination_bucket=destination_bucket,
        destination_key=destination_key,
        user_id=current_user.id,
    )

    result = await services.copy_file(
        source_bucket=source_bucket,
        source_key=source_key,
        destination_bucket=destination_bucket,
        destination_key=destination_key,
        metadata=request.metadata,
    )

    logger.info(
        "File copied",
        source_bucket=source_bucket,
        source_key=source_key,
        destination_bucket=destination_bucket,
        destination_key=destination_key,
        user_id=current_user.id,
    )
    return result


@router.post(
    "/files/move",
    response_model=schemas.FileMoveResponse,
    status_code=status.HTTP_200_OK,
    summary="Move file",
    description="Move a file within or between buckets",
)
async def move_file(
    request: schemas.FileMoveRequest,
    current_user: UserInfo = Depends(get_current_user),
) -> schemas.FileMoveResponse:
    """Move file within or between buckets.

    Moves a file by copying it to the destination and then deleting the original.
    The file is moved atomically (copy succeeds before delete).

    Args:
        request: File move request with source and destination information
        current_user: Current authenticated user (injected via dependency)

    Returns:
        File move response with source and destination information

    Raises:
        S3FileNotFoundError: If source file doesn't exist
        S3BucketNotFoundError: If bucket doesn't exist
        S3UploadError: If move fails
    """
    # Validate all bucket and key parameters to prevent path traversal
    source_bucket = validate_s3_bucket_name(request.source_bucket)
    source_key = validate_s3_key(request.source_key)
    destination_bucket = validate_s3_bucket_name(request.destination_bucket)
    destination_key = validate_s3_key(request.destination_key)

    logger.debug(
        "Moving file",
        source_bucket=source_bucket,
        source_key=source_key,
        destination_bucket=destination_bucket,
        destination_key=destination_key,
        user_id=current_user.id,
    )

    result = await services.move_file(
        source_bucket=source_bucket,
        source_key=source_key,
        destination_bucket=destination_bucket,
        destination_key=destination_key,
        metadata=request.metadata,
    )

    logger.info(
        "File moved",
        source_bucket=source_bucket,
        source_key=source_key,
        destination_bucket=destination_bucket,
        destination_key=destination_key,
        user_id=current_user.id,
    )
    return result


@router.post(
    "/files/batch-delete",
    response_model=schemas.BatchDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch delete files",
    description="Delete multiple files in a single request",
)
async def batch_delete_files(
    request: schemas.BatchDeleteRequest,
    current_user: UserInfo = Depends(get_current_user),
) -> schemas.BatchDeleteResponse:
    """Delete multiple files in a single request.

    Deletes up to 1000 files in a single batch operation.
    Returns results for each file (success or error).

    Args:
        request: Batch delete request with bucket and list of keys
        current_user: Current authenticated user (injected via dependency)

    Returns:
        Batch delete response with deleted keys and errors

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3DownloadError: If deletion fails
    """
    # Validate bucket and all keys to prevent path traversal
    bucket = validate_s3_bucket_name(request.bucket)
    validated_keys = [validate_s3_key(key) for key in request.keys]

    logger.debug(
        "Batch deleting files",
        bucket=bucket,
        count=len(validated_keys),
        user_id=current_user.id,
    )

    result = await services.batch_delete_files(bucket, validated_keys)

    logger.info(
        "Files batch deleted",
        bucket=request.bucket,
        deleted_count=len(result.deleted),
        error_count=len(result.errors),
        user_id=current_user.id,
    )
    return result


@router.post(
    "/files/delete-prefix",
    response_model=schemas.DeletePrefixResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete files by prefix",
    description="Delete all files matching a prefix",
)
async def delete_files_by_prefix(
    request: schemas.DeletePrefixRequest,
    current_user: UserInfo = Depends(get_current_user),
) -> schemas.DeletePrefixResponse:
    """Delete files by prefix.

    Deletes all files in a bucket that match the specified prefix.
    Useful for deleting entire "folders" or file groups.

    Args:
        request: Delete prefix request with bucket, prefix, and max keys
        current_user: Current authenticated user (injected via dependency)

    Returns:
        Delete prefix response with count and list of deleted keys

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3DownloadError: If deletion fails
    """
    # Validate bucket and prefix to prevent path traversal
    bucket = validate_s3_bucket_name(request.bucket)
    prefix = validate_s3_key(request.prefix) if request.prefix else ""

    logger.debug(
        "Deleting files by prefix",
        bucket=bucket,
        prefix=prefix,
        user_id=current_user.id,
    )

    result = await services.delete_files_by_prefix(bucket, prefix, request.max_keys)

    logger.info(
        "Files deleted by prefix",
        bucket=bucket,
        prefix=prefix,
        deleted_count=result.deleted_count,
        user_id=current_user.id,
    )
    return result


@router.get(
    "/files/versions/{bucket}/{key:path}",
    response_model=schemas.FileVersionsResponse,
    status_code=status.HTTP_200_OK,
    summary="List file versions",
    description="List all versions of a file",
)
async def list_file_versions(
    bucket: str,
    key: str,
    current_user: UserInfo = Depends(get_current_user),
) -> schemas.FileVersionsResponse:
    """List all versions of a file.

    Retrieves a list of all versions of a file if versioning is enabled
    on the bucket. Each version has a unique version ID.

    Args:
        bucket: Bucket name containing the file
        key: File key (path) within the bucket
        current_user: Current authenticated user (injected via dependency)

    Returns:
        File versions response with list of versions

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3DownloadError: If listing fails
    """
    # Validate bucket and key to prevent path traversal
    bucket = validate_s3_bucket_name(bucket)
    key = validate_s3_key(key)

    logger.debug(
        "Listing file versions", bucket=bucket, key=key, user_id=current_user.id
    )

    result = await services.list_file_versions(bucket, key)

    logger.info(
        "File versions listed",
        bucket=bucket,
        key=key,
        version_count=len(result.versions),
        user_id=current_user.id,
    )
    return result


@router.get(
    "/files/download-version/{bucket}/{key:path}",
    status_code=status.HTTP_200_OK,
    summary="Download file version",
    description="Download a specific version of a file",
)
async def download_file_version(
    bucket: str,
    key: str,
    version_id: str = Query(..., description="Version ID to download"),
    current_user: UserInfo = Depends(get_current_user),
) -> StreamingResponse:
    """Download a specific version of a file.

    Downloads a specific version of a file by version ID.
    Requires versioning to be enabled on the bucket.

    Args:
        bucket: Bucket name containing the file
        key: File key (path) within the bucket
        version_id: Version ID to download
        current_user: Current authenticated user (injected via dependency)

    Returns:
        Streaming response with file data and content type

    Raises:
        S3FileNotFoundError: If version doesn't exist
        S3BucketNotFoundError: If bucket doesn't exist
        S3DownloadError: If download fails
    """
    # Validate bucket and key to prevent path traversal
    bucket = validate_s3_bucket_name(bucket)
    key = validate_s3_key(key)

    logger.debug(
        "Downloading file version",
        bucket=bucket,
        key=key,
        version_id=version_id,
        user_id=current_user.id,
    )

    file_data, content_type = await services.download_file_version(
        bucket, key, version_id
    )

    logger.info(
        "File version downloaded",
        bucket=bucket,
        key=key,
        version_id=version_id,
        user_id=current_user.id,
    )

    return StreamingResponse(
        iter([file_data]),
        media_type=content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{key.split("/")[-1]}"',
        },
    )


@router.delete(
    "/files/version/{bucket}/{key:path}",
    status_code=status.HTTP_200_OK,
    summary="Delete file version",
    description="Delete a specific version of a file",
)
async def delete_file_version(
    bucket: str,
    key: str,
    version_id: str = Query(..., description="Version ID to delete"),
    current_user: UserInfo = Depends(get_current_user),
) -> ORJSONResponse:
    """Delete a specific version of a file.

    Deletes a specific version of a file by version ID.
    Requires versioning to be enabled on the bucket.

    Args:
        bucket: Bucket name containing the file
        key: File key (path) within the bucket
        version_id: Version ID to delete
        current_user: Current authenticated user (injected via dependency)

    Returns:
        JSON response confirming deletion

    Raises:
        S3FileNotFoundError: If version doesn't exist
        S3BucketNotFoundError: If bucket doesn't exist
        S3DownloadError: If deletion fails
    """
    # Validate bucket and key to prevent path traversal
    bucket = validate_s3_bucket_name(bucket)
    key = validate_s3_key(key)

    logger.debug(
        "Deleting file version",
        bucket=bucket,
        key=key,
        version_id=version_id,
        user_id=current_user.id,
    )

    await services.delete_file_version(bucket, key, version_id)

    logger.info(
        "File version deleted",
        bucket=bucket,
        key=key,
        version_id=version_id,
        user_id=current_user.id,
    )

    return ORJSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "File version deleted successfully",
            "bucket": bucket,
            "key": key,
            "version_id": version_id,
        },
    )


@router.get(
    "/buckets/{bucket_name}/versioning",
    response_model=schemas.BucketVersioningResponse,
    status_code=status.HTTP_200_OK,
    summary="Get bucket versioning",
    description="Get versioning configuration for a bucket",
)
async def get_bucket_versioning(
    bucket_name: str,
    current_user: UserInfo = Depends(get_current_user),
) -> schemas.BucketVersioningResponse:
    """Get bucket versioning configuration.

    Retrieves the versioning configuration for the specified bucket.

    Args:
        bucket_name: Name of the bucket
        current_user: Current authenticated user (injected via dependency)

    Returns:
        Bucket versioning response with status

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3DownloadError: If retrieval fails
    """
    # Validate bucket name to prevent path traversal
    bucket_name = validate_s3_bucket_name(bucket_name)

    logger.debug(
        "Getting bucket versioning", bucket_name=bucket_name, user_id=current_user.id
    )

    result = await services.get_bucket_versioning(bucket_name)

    logger.info(
        "Bucket versioning retrieved", bucket_name=bucket_name, user_id=current_user.id
    )
    return result


@router.put(
    "/buckets/{bucket_name}/versioning",
    response_model=schemas.BucketVersioningResponse,
    status_code=status.HTTP_200_OK,
    summary="Set bucket versioning",
    description="Enable or suspend versioning for a bucket",
)
async def set_bucket_versioning(
    bucket_name: str,
    request: schemas.BucketVersioningRequest,
    current_user: UserInfo = Depends(get_current_user),
) -> schemas.BucketVersioningResponse:
    """Set bucket versioning configuration.

    Enables or suspends versioning for the specified bucket.
    Once enabled, all file changes create new versions.

    Args:
        bucket_name: Name of the bucket
        request: Versioning request with status (Enabled or Suspended)
        current_user: Current authenticated user (injected via dependency)

    Returns:
        Bucket versioning response with updated status

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3UploadError: If setting fails
    """
    # Validate bucket name to prevent path traversal
    bucket_name = validate_s3_bucket_name(bucket_name)

    logger.debug(
        "Setting bucket versioning",
        bucket_name=bucket_name,
        status=request.status,
        user_id=current_user.id,
    )

    result = await services.set_bucket_versioning(bucket_name, request.status)

    logger.info(
        "Bucket versioning set",
        bucket_name=bucket_name,
        status=request.status,
        user_id=current_user.id,
    )
    return result


@router.get(
    "/buckets/{bucket_name}/lifecycle",
    response_model=schemas.BucketLifecycleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get bucket lifecycle",
    description="Get lifecycle configuration for a bucket",
)
async def get_bucket_lifecycle(
    bucket_name: str,
    current_user: UserInfo = Depends(get_current_user),
) -> schemas.BucketLifecycleResponse:
    """Get bucket lifecycle configuration.

    Retrieves the lifecycle configuration for the specified bucket.

    Args:
        bucket_name: Name of the bucket
        current_user: Current authenticated user (injected via dependency)

    Returns:
        Bucket lifecycle response with rules

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3DownloadError: If retrieval fails
    """
    # Validate bucket name to prevent path traversal
    bucket_name = validate_s3_bucket_name(bucket_name)

    logger.debug(
        "Getting bucket lifecycle", bucket_name=bucket_name, user_id=current_user.id
    )

    result = await services.get_bucket_lifecycle(bucket_name)

    logger.info(
        "Bucket lifecycle retrieved", bucket_name=bucket_name, user_id=current_user.id
    )
    return result


@router.put(
    "/buckets/{bucket_name}/lifecycle",
    response_model=schemas.BucketLifecycleResponse,
    status_code=status.HTTP_200_OK,
    summary="Set bucket lifecycle",
    description="Set lifecycle configuration for a bucket",
)
async def set_bucket_lifecycle(
    bucket_name: str,
    request: schemas.BucketLifecycleRequest,
    current_user: UserInfo = Depends(get_current_user),
) -> schemas.BucketLifecycleResponse:
    """Set bucket lifecycle configuration.

    Sets lifecycle rules for the specified bucket. Rules can include
    expiration, transitions to different storage classes, etc.

    Args:
        bucket_name: Name of the bucket
        request: Lifecycle request with rules
        current_user: Current authenticated user (injected via dependency)

    Returns:
        Bucket lifecycle response with rules

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3UploadError: If setting fails
    """
    # Validate bucket name to prevent path traversal
    bucket_name = validate_s3_bucket_name(bucket_name)

    logger.debug(
        "Setting bucket lifecycle",
        bucket_name=bucket_name,
        rules_count=len(request.rules),
        user_id=current_user.id,
    )

    # Convert Pydantic models to dicts
    rules_dict = [rule.model_dump() for rule in request.rules]

    result = await services.set_bucket_lifecycle(bucket_name, rules_dict)

    logger.info(
        "Bucket lifecycle set",
        bucket_name=bucket_name,
        rules_count=len(request.rules),
        user_id=current_user.id,
    )
    return result


@router.get(
    "/buckets/{bucket_name}/cors",
    response_model=schemas.BucketCORSResponse,
    status_code=status.HTTP_200_OK,
    summary="Get bucket CORS",
    description="Get CORS configuration for a bucket",
)
async def get_bucket_cors(
    bucket_name: str,
    current_user: UserInfo = Depends(get_current_user),
) -> schemas.BucketCORSResponse:
    """Get bucket CORS configuration.

    Retrieves the CORS configuration for the specified bucket.

    Args:
        bucket_name: Name of the bucket
        current_user: Current authenticated user (injected via dependency)

    Returns:
        Bucket CORS response with rules

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3DownloadError: If retrieval fails
    """
    # Validate bucket name to prevent path traversal
    bucket_name = validate_s3_bucket_name(bucket_name)

    logger.debug(
        "Getting bucket CORS", bucket_name=bucket_name, user_id=current_user.id
    )

    result = await services.get_bucket_cors(bucket_name)

    logger.info(
        "Bucket CORS retrieved", bucket_name=bucket_name, user_id=current_user.id
    )
    return result


@router.put(
    "/buckets/{bucket_name}/cors",
    response_model=schemas.BucketCORSResponse,
    status_code=status.HTTP_200_OK,
    summary="Set bucket CORS",
    description="Set CORS configuration for a bucket",
)
async def set_bucket_cors(
    bucket_name: str,
    request: schemas.BucketCORSRequest,
    current_user: UserInfo = Depends(get_current_user),
) -> schemas.BucketCORSResponse:
    """Set bucket CORS configuration.

    Sets CORS rules for the specified bucket. CORS rules allow
    browsers to access S3 resources from different origins.

    Args:
        bucket_name: Name of the bucket
        request: CORS request with rules
        current_user: Current authenticated user (injected via dependency)

    Returns:
        Bucket CORS response with rules

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3UploadError: If setting fails
    """
    # Validate bucket name to prevent path traversal
    bucket_name = validate_s3_bucket_name(bucket_name)

    logger.debug(
        "Setting bucket CORS",
        bucket_name=bucket_name,
        rules_count=len(request.cors_rules),
        user_id=current_user.id,
    )

    # Convert Pydantic models to dicts
    cors_rules_dict = [rule.model_dump() for rule in request.cors_rules]

    result = await services.set_bucket_cors(bucket_name, cors_rules_dict)

    logger.info(
        "Bucket CORS set",
        bucket_name=bucket_name,
        rules_count=len(request.cors_rules),
        user_id=current_user.id,
    )
    return result


@router.get(
    "/buckets/{bucket_name}/notifications",
    response_model=schemas.BucketNotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get bucket notifications",
    description="Get notification configuration for a bucket",
)
async def get_bucket_notifications(
    bucket_name: str,
    current_user: UserInfo = Depends(get_current_user),
) -> schemas.BucketNotificationResponse:
    """Get bucket notification configuration.

    Retrieves the notification configuration for the specified bucket.

    Args:
        bucket_name: Name of the bucket
        current_user: Current authenticated user (injected via dependency)

    Returns:
        Bucket notification response with configurations

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3DownloadError: If retrieval fails
    """
    # Validate bucket name to prevent path traversal
    bucket_name = validate_s3_bucket_name(bucket_name)

    logger.debug(
        "Getting bucket notifications", bucket_name=bucket_name, user_id=current_user.id
    )

    result = await services.get_bucket_notifications(bucket_name)

    logger.info(
        "Bucket notifications retrieved",
        bucket_name=bucket_name,
        user_id=current_user.id,
    )
    return result


@router.put(
    "/buckets/{bucket_name}/notifications",
    response_model=schemas.BucketNotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Set bucket notifications",
    description="Set notification configuration for a bucket",
)
async def set_bucket_notifications(
    bucket_name: str,
    request: schemas.BucketNotificationRequest,
    current_user: UserInfo = Depends(get_current_user),
) -> schemas.BucketNotificationResponse:
    """Set bucket notification configuration.

    Sets notification rules for the specified bucket. Notifications
    can be sent to SQS, SNS, or Lambda functions when events occur.

    Note: Webhook notifications require SNS topic and Lambda function setup.

    Args:
        bucket_name: Name of the bucket
        request: Notification request with events, filters, and webhook URL
        current_user: Current authenticated user (injected via dependency)

    Returns:
        Bucket notification response with configurations

    Raises:
        S3BucketNotFoundError: If bucket doesn't exist
        S3UploadError: If setting fails
    """
    # Validate bucket name to prevent path traversal
    bucket_name = validate_s3_bucket_name(bucket_name)

    logger.debug(
        "Setting bucket notifications",
        bucket_name=bucket_name,
        events_count=len(request.events),
        user_id=current_user.id,
    )

    # Convert Pydantic models to dicts
    filters_dict = (
        [filter.model_dump() for filter in request.filters] if request.filters else None
    )

    result = await services.set_bucket_notifications(
        bucket_name,
        request.events,
        filters_dict,
        request.webhook_url,
    )

    logger.info(
        "Bucket notifications set",
        bucket_name=bucket_name,
        events_count=len(request.events),
        user_id=current_user.id,
    )
    return result
