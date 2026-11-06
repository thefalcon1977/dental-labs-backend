"""Type aliases for S3 module."""

from typing import Any, TypeAlias

# Dictionary type aliases
MetadataDict: TypeAlias = dict[str, str]
PolicyDict: TypeAlias = dict[str, Any]
FileMetadataDict: TypeAlias = dict[str, Any]
FileListDict: TypeAlias = dict[str, Any]
UploadResultDict: TypeAlias = dict[str, Any]
MultipartInitResultDict: TypeAlias = dict[str, Any]
MultipartPartResultDict: TypeAlias = dict[str, Any]
MultipartCompleteResultDict: TypeAlias = dict[str, Any]
BucketDict: TypeAlias = dict[str, Any]
BucketList: TypeAlias = list[BucketDict]
FileDict: TypeAlias = dict[str, Any]
FileList: TypeAlias = list[FileDict]
MultipartPartDict: TypeAlias = dict[str, Any]
MultipartPartsList: TypeAlias = list[MultipartPartDict]
CopyResultDict: TypeAlias = dict[str, Any]
MoveResultDict: TypeAlias = dict[str, Any]
BatchDeleteResultDict: TypeAlias = dict[str, Any]
VersionInfoDict: TypeAlias = dict[str, Any]
VersionListDict: TypeAlias = dict[str, Any]
VersioningConfigDict: TypeAlias = dict[str, Any]
LifecycleRuleDict: TypeAlias = dict[str, Any]
LifecycleConfigDict: TypeAlias = dict[str, Any]
CORSRuleDict: TypeAlias = dict[str, Any]
CORSConfigDict: TypeAlias = dict[str, Any]
NotificationConfigDict: TypeAlias = dict[str, Any]
NotificationListDict: TypeAlias = dict[str, Any]

__all__ = [
    "MetadataDict",
    "PolicyDict",
    "FileMetadataDict",
    "FileListDict",
    "UploadResultDict",
    "MultipartInitResultDict",
    "MultipartPartResultDict",
    "MultipartCompleteResultDict",
    "BucketDict",
    "BucketList",
    "FileDict",
    "FileList",
    "MultipartPartDict",
    "MultipartPartsList",
    "CopyResultDict",
    "MoveResultDict",
    "BatchDeleteResultDict",
    "VersionInfoDict",
    "VersionListDict",
    "VersioningConfigDict",
    "LifecycleRuleDict",
    "LifecycleConfigDict",
    "CORSRuleDict",
    "CORSConfigDict",
    "NotificationConfigDict",
    "NotificationListDict",
]
