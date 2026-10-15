"""Storage infrastructure for Document module.

Provides file storage services via MinIO.
"""

from src.modules.document.infrastructure.storage.storage import (
    close,
    delete_file,
    download_bytes,
    download_file,
    file_exists,
    get_client,
    get_presigned_url,
    upload_bytes,
    upload_file,
)

__all__ = [
    "get_client",
    "upload_file",
    "upload_bytes",
    "download_file",
    "download_bytes",
    "delete_file",
    "get_presigned_url",
    "file_exists",
    "close",
]
