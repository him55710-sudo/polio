from __future__ import annotations

import os
from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
import tempfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import BinaryIO
    from collections.abc import Iterator


class StorageProvider(ABC):
    """Abstract interface for storage operations."""

    @abstractmethod
    def store(self, content: bytes, path: str) -> str:
        """
        Stores content and returns a resolvable path or key.
        :param content: Binary content to store.
        :param path: Destination path or key.
        :return: The stored path or key.
        """
        pass

    @abstractmethod
    def retrieve(self, path: str) -> bytes:
        """
        Retrieves binary content from the specified path or key.
        :param path: Path or key to retrieve from.
        :return: Binary content.
        """
        pass

    @abstractmethod
    def delete(self, path: str) -> None:
        """
        Deletes the content at the specified path or key.
        :param path: Path or key to delete.
        """
        pass

    @abstractmethod
    def exists(self, path: str) -> bool:
        """
        Checks if content exists at the specified path or key.
        :param path: Path or key to check.
        :return: True if exists, False otherwise.
        """
        pass

    @abstractmethod
    def get_url(self, path: str) -> str:
        """
        Returns a URL or local filesystem path for the specified key.
        """
        pass


class LocalStorageProvider(StorageProvider):
    """Stores files on the local filesystem."""

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def store(self, content: bytes, path: str) -> str:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return path

    def retrieve(self, path: str) -> bytes:
        target = self.root / path
        if not target.exists():
            raise FileNotFoundError(f"File not found in local storage: {path}")
        return target.read_bytes()

    def delete(self, path: str) -> None:
        target = self.root / path
        if target.exists():
            target.unlink()

    def exists(self, path: str) -> bool:
        return (self.root / path).exists()

    def get_url(self, path: str) -> str:
        return str(self.root / path)


class S3StorageProvider(StorageProvider):
    """Stores files on S3-compatible object storage."""

    def __init__(
        self,
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        bucket_name: str | None = None,
        region_name: str | None = None,
    ):
        try:
            import boto3
        except ImportError:
            raise ImportError("boto3 is required for S3StorageProvider. Run `pip install boto3`.")

        self.bucket_name = bucket_name
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region_name,
        )

    def store(self, content: bytes, path: str) -> str:
        self.client.put_object(
            Bucket=self.bucket_name,
            Key=path,
            Body=content,
        )
        return path

    def retrieve(self, path: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket_name, Key=path)
        return response["Body"].read()

    def delete(self, path: str) -> None:
        self.client.delete_object(Bucket=self.bucket_name, Key=path)

    def exists(self, path: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=path)
            return True
        except Exception:
            return False

    def get_url(self, path: str) -> str:
        # NOTE: This might need to generate signed URLs if the bucket is private.
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": path},
            ExpiresIn=3600,
        )


def get_storage_provider(settings=None) -> StorageProvider:
    """Factory to get the configured storage provider."""
    from polio_shared.paths import get_storage_root

    if settings is None:
        try:
            from polio_api.core.config import get_settings  # type: ignore

            settings = get_settings()
        except Exception:  # noqa: BLE001
            class _FallbackSettings:  # pragma: no cover - defensive fallback for isolated package use.
                polio_storage_provider = os.getenv("POLIO_STORAGE_PROVIDER", "local")
                polio_storage_root = os.getenv("POLIO_STORAGE_ROOT") or os.getenv("LOCAL_OBJECT_STORE_PATH")
                s3_endpoint_url = os.getenv("S3_ENDPOINT_URL") or os.getenv("OBJECT_STORAGE_ENDPOINT")
                s3_access_key_id = os.getenv("S3_ACCESS_KEY_ID") or os.getenv("OBJECT_STORAGE_ACCESS_KEY")
                s3_secret_access_key = os.getenv("S3_SECRET_ACCESS_KEY") or os.getenv("OBJECT_STORAGE_SECRET_KEY")
                s3_bucket_name = os.getenv("S3_BUCKET_NAME") or os.getenv("OBJECT_STORAGE_BUCKET")
                s3_region_name = os.getenv("S3_REGION_NAME")

            settings = _FallbackSettings()

    provider_type = getattr(settings, "polio_storage_provider", "local").lower()

    if provider_type == "s3":
        return S3StorageProvider(
            endpoint_url=getattr(settings, "s3_endpoint_url", None),
            access_key_id=getattr(settings, "s3_access_key_id", None),
            secret_access_key=getattr(settings, "s3_secret_access_key", None),
            bucket_name=getattr(settings, "s3_bucket_name", None),
            region_name=getattr(settings, "s3_region_name", None),
        )

    configured_root = getattr(settings, "polio_storage_root", None)
    if configured_root:
        return LocalStorageProvider(root=Path(configured_root))
    return LocalStorageProvider(root=get_storage_root())


def get_storage_provider_name(storage: StorageProvider) -> str:
    if isinstance(storage, S3StorageProvider):
        return "s3"
    return "local"


@contextmanager
def materialize_storage_path(
    storage: StorageProvider,
    path: str,
    *,
    suffix: str | None = None,
) -> Iterator[Path]:
    """
    Yields a local filesystem path for a stored object.

    - Local provider: reuses the real local path when available.
    - Remote provider: downloads bytes into a temp file and removes it after use.
    """
    if isinstance(storage, LocalStorageProvider):
        local_path = Path(storage.get_url(path))
        if local_path.exists():
            yield local_path
            return

    content = storage.retrieve(path)
    materialized_suffix = suffix if suffix is not None else Path(path).suffix
    with tempfile.NamedTemporaryFile(prefix="polio-storage-", suffix=materialized_suffix or "", delete=False) as temp:
        temp.write(content)
        temp_path = Path(temp.name)

    try:
        yield temp_path
    finally:
        if temp_path.exists():
            temp_path.unlink()


def materialize_storage_path_once(
    storage: StorageProvider,
    path: str,
    *,
    suffix: str | None = None,
) -> tuple[Path, bool]:
    """
    Returns (local_path, cleanup_required).

    cleanup_required is True when a temporary file was created.
    """
    if isinstance(storage, LocalStorageProvider):
        local_path = Path(storage.get_url(path))
        if local_path.exists():
            return local_path, False

    content = storage.retrieve(path)
    materialized_suffix = suffix if suffix is not None else Path(path).suffix
    with tempfile.NamedTemporaryFile(prefix="polio-storage-", suffix=materialized_suffix or "", delete=False) as temp:
        temp.write(content)
        temp_path = Path(temp.name)
    return temp_path, True
