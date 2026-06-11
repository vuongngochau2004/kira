"""MinIO Storage Adapter — implements StoragePort.

Wraps the existing MinIO client functions from
src.modules.document.infrastructure.storage.storage.
"""
from src.shared.ports.storage import StoragePort
from src.modules.document.infrastructure.storage.storage import (
    upload_bytes,
    download_bytes,
    delete_file,
    file_exists,
    get_presigned_url,
)


class MinIOAdapter(StoragePort):
    """Adapter for MinIO Object Storage."""

    async def upload(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload file to MinIO and return presigned URL."""
        upload_bytes(data, object_name=key, content_type=content_type)
        return get_presigned_url(object_name=key)

    async def download(self, key: str) -> bytes:
        """Download bytes from MinIO."""
        if not file_exists(object_name=key):
            raise FileNotFoundError(f"File {key} not found in MinIO storage.")
        return download_bytes(object_name=key)

    async def delete(self, key: str) -> None:
        """Delete object from MinIO."""
        delete_file(object_name=key)

    async def exists(self, key: str) -> bool:
        """Check if object exists in MinIO."""
        return file_exists(object_name=key)
