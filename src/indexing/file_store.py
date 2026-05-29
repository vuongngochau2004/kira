"""MinIO file storage wrapper."""

import sys
from pathlib import Path
from datetime import timedelta
from typing import BinaryIO

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from minio import Minio

from config.config import settings


# Singleton client
_minio_client: Minio | None = None


def get_client() -> Minio:
    """Get MinIO client singleton."""
    global _minio_client
    if _minio_client is None:
        _minio_client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        # Ensure bucket exists
        _ensure_bucket()
    return _minio_client


def _ensure_bucket() -> None:
    """Ensure default bucket exists."""
    client = get_client()
    try:
        if not client.bucket_exists(settings.minio_bucket):
            client.make_bucket(settings.minio_bucket)
    except Exception:
        pass


def upload_file(
    file_path: str | Path,
    object_name: str,
    bucket_name: str | None = None,
    content_type: str | None = None,
) -> bool:
    """Upload a file to MinIO.

    Args:
        file_path: Local file path to upload
        object_name: Object name in MinIO
        bucket_name: Bucket name (uses default if not specified)
        content_type: MIME type of the file

    Returns:
        True if successful
    """
    client = get_client()
    bucket = bucket_name or settings.minio_bucket

    client.fput_object(
        bucket_name=bucket,
        object_name=object_name,
        file_path=str(file_path),
        content_type=content_type,
    )

    return True


def upload_bytes(
    data: bytes,
    object_name: str,
    bucket_name: str | None = None,
    content_type: str | None = None,
) -> bool:
    """Upload bytes to MinIO.

    Args:
        data: Bytes to upload
        object_name: Object name in MinIO
        bucket_name: Bucket name (uses default if not specified)
        content_type: MIME type of the data

    Returns:
        True if successful
    """
    import io

    client = get_client()
    bucket = bucket_name or settings.minio_bucket

    client.put_object(
        bucket_name=bucket,
        object_name=object_name,
        data=io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )

    return True


def download_file(
    object_name: str,
    file_path: str | Path,
    bucket_name: str | None = None,
) -> None:
    """Download a file from MinIO.

    Args:
        object_name: Object name in MinIO
        file_path: Local file path to save
        bucket_name: Bucket name (uses default if not specified)
    """
    client = get_client()
    bucket = bucket_name or settings.minio_bucket

    client.fget_object(
        bucket_name=bucket,
        object_name=object_name,
        file_path=str(file_path),
    )


def download_bytes(
    object_name: str,
    bucket_name: str | None = None,
) -> bytes:
    """Download bytes from MinIO.

    Args:
        object_name: Object name in MinIO
        bucket_name: Bucket name (uses default if not specified)

    Returns:
        File content as bytes
    """
    client = get_client()
    bucket = bucket_name or settings.minio_bucket

    response = client.get_object(bucket_name=bucket, object_name=object_name)
    data = response.read()
    response.close()
    response.release_conn()

    return data


def delete_file(
    object_name: str,
    bucket_name: str | None = None,
) -> None:
    """Delete a file from MinIO.

    Args:
        object_name: Object name in MinIO
        bucket_name: Bucket name (uses default if not specified)
    """
    client = get_client()
    bucket = bucket_name or settings.minio_bucket

    client.remove_object(bucket_name=bucket, object_name=object_name)


def get_presigned_url(
    object_name: str,
    expires: int = 3600,
    bucket_name: str | None = None,
) -> str:
    """Generate a presigned URL for download.

    Args:
        object_name: Object name in MinIO
        expires: URL expiration time in seconds
        bucket_name: Bucket name (uses default if not specified)

    Returns:
        Presigned URL string
    """
    client = get_client()
    bucket = bucket_name or settings.minio_bucket

    return client.presigned_get_object(
        bucket_name=bucket,
        object_name=object_name,
        expires=timedelta(seconds=expires),
    )


def file_exists(
    object_name: str,
    bucket_name: str | None = None,
) -> bool:
    """Check if a file exists in MinIO.

    Args:
        object_name: Object name in MinIO
        bucket_name: Bucket name (uses default if not specified)

    Returns:
        True if file exists
    """
    client = get_client()
    bucket = bucket_name or settings.minio_bucket

    try:
        client.stat_object(bucket_name=bucket, object_name=object_name)
        return True
    except Exception:
        return False


async def close() -> None:
    """Close MinIO client connection."""
    global _minio_client
    _minio_client = None


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
