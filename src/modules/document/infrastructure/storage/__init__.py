"""Storage infrastructure for Document module.

Provides file storage services via MinIO.
"""

from src.modules.document.infrastructure.storage.storage import (
    get_client,
    upload_file,
    upload_bytes,
    download_file,
    download_bytes,
    delete_file,
    get_presigned_url,
    file_exists,
    close,
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
