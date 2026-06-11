"""Port: Object storage contract.

Application core depends on this ABC, NOT on MinIO/S3 directly.
Allows swapping MinIO ↔ AWS S3 ↔ Google Cloud Storage
without changing business logic.
"""
from abc import ABC, abstractmethod


class StoragePort(ABC):
    """Port: what the application needs from any object storage.

    Example:
        >>> class MyStorage(StoragePort):
        ...     async def upload(self, key, data, content_type="application/octet-stream"):
        ...         return "https://bucket/key"
    """

    @abstractmethod
    async def upload(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload file to object storage.

        Args:
            key: Object key/path in the storage bucket
            data: File content as bytes
            content_type: MIME type of the file

        Returns:
            URL to access the uploaded file (presigned or public)
        """
        ...

    @abstractmethod
    async def download(self, key: str) -> bytes:
        """Download file from object storage.

        Args:
            key: Object key/path in the storage bucket

        Returns:
            File content as bytes

        Raises:
            FileNotFoundError: If key does not exist
        """
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete file from object storage.

        Args:
            key: Object key/path to delete
        """
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if file exists in object storage.

        Args:
            key: Object key/path to check

        Returns:
            True if file exists, False otherwise
        """
        ...
