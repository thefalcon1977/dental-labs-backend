"""S3/MinIO-related Prometheus metrics."""

from prometheus_client import Counter, Gauge, Histogram

# Active Operations
s3_active_operations = Gauge(
    "s3_active_operations",
    "Number of active S3 operations",
    ["operation"],
)

# General Operation Metrics
s3_operations_total = Counter(
    "s3_operations_total",
    "Total number of S3 operations",
    ["operation", "bucket", "status"],
)

s3_operation_duration_seconds = Histogram(
    "s3_operation_duration_seconds",
    "S3 operation duration in seconds",
    ["operation", "bucket"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

s3_errors_total = Counter(
    "s3_errors_total",
    "Total number of S3 operation errors",
    ["operation", "bucket", "error_type"],
)

s3_file_size_bytes = Histogram(
    "s3_file_size_bytes",
    "S3 file size in bytes",
    ["operation", "bucket"],
    buckets=(
        1024,  # 1 KB
        10240,  # 10 KB
        102400,  # 100 KB
        1048576,  # 1 MB
        10485760,  # 10 MB
        104857600,  # 100 MB
        1073741824,  # 1 GB
    ),
)

# Upload Metrics
s3_uploads_total = Counter(
    "s3_uploads_total",
    "Total number of file uploads",
    ["bucket", "status"],
)

s3_upload_duration_seconds = Histogram(
    "s3_upload_duration_seconds",
    "File upload duration in seconds",
    ["bucket"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

s3_upload_size_bytes = Histogram(
    "s3_upload_size_bytes",
    "Uploaded file size in bytes",
    ["bucket"],
    buckets=(
        1024,  # 1 KB
        10240,  # 10 KB
        102400,  # 100 KB
        1048576,  # 1 MB
        10485760,  # 10 MB
        104857600,  # 100 MB
        1073741824,  # 1 GB
    ),
)

# Download Metrics
s3_downloads_total = Counter(
    "s3_downloads_total",
    "Total number of file downloads",
    ["bucket", "status"],
)

s3_download_duration_seconds = Histogram(
    "s3_download_duration_seconds",
    "File download duration in seconds",
    ["bucket"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

s3_download_size_bytes = Histogram(
    "s3_download_size_bytes",
    "Downloaded file size in bytes",
    ["bucket"],
    buckets=(
        1024,  # 1 KB
        10240,  # 10 KB
        102400,  # 100 KB
        1048576,  # 1 MB
        10485760,  # 10 MB
        104857600,  # 100 MB
        1073741824,  # 1 GB
    ),
)

# Bucket Operation Metrics
s3_bucket_operations_total = Counter(
    "s3_bucket_operations_total",
    "Total number of bucket operations",
    ["operation", "status"],
)

s3_bucket_operation_duration_seconds = Histogram(
    "s3_bucket_operation_duration_seconds",
    "Bucket operation duration in seconds",
    ["operation"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Presigned URL Metrics
s3_presigned_urls_generated_total = Counter(
    "s3_presigned_urls_generated_total",
    "Total number of presigned URLs generated",
    ["bucket"],
)

s3_presigned_url_generation_duration_seconds = Histogram(
    "s3_presigned_url_generation_duration_seconds",
    "Presigned URL generation duration in seconds",
    ["bucket"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
)

# Multipart Upload Metrics
s3_multipart_uploads_total = Counter(
    "s3_multipart_uploads_total",
    "Total number of multipart uploads",
    ["bucket", "status"],
)

s3_multipart_upload_duration_seconds = Histogram(
    "s3_multipart_upload_duration_seconds",
    "Multipart upload duration in seconds",
    ["bucket"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)

s3_multipart_upload_parts_total = Counter(
    "s3_multipart_upload_parts_total",
    "Total number of multipart upload parts",
    ["bucket", "status"],
)

s3_multipart_upload_part_size_bytes = Histogram(
    "s3_multipart_upload_part_size_bytes",
    "Multipart upload part size in bytes",
    ["bucket"],
    buckets=(
        5242880,  # 5 MB (common part size)
        10485760,  # 10 MB
        52428800,  # 50 MB
        104857600,  # 100 MB
    ),
)

__all__ = [
    "s3_active_operations",
    "s3_operations_total",
    "s3_operation_duration_seconds",
    "s3_errors_total",
    "s3_file_size_bytes",
    "s3_uploads_total",
    "s3_upload_duration_seconds",
    "s3_upload_size_bytes",
    "s3_downloads_total",
    "s3_download_duration_seconds",
    "s3_download_size_bytes",
    "s3_bucket_operations_total",
    "s3_bucket_operation_duration_seconds",
    "s3_presigned_urls_generated_total",
    "s3_presigned_url_generation_duration_seconds",
    "s3_multipart_uploads_total",
    "s3_multipart_upload_duration_seconds",
    "s3_multipart_upload_parts_total",
    "s3_multipart_upload_part_size_bytes",
]
