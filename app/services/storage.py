import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, Optional, Union
from werkzeug.datastructures import FileStorage


class StorageService(ABC):
    """
    Abstract file storage interface conforming to PRD Section 8.
    Isolates file handling from storage provider to ensure zero-code-change
    portability between local dev filesystem and durable S3/cloud storage.
    """

    @abstractmethod
    def save(self, file_data: Union[FileStorage, BinaryIO, bytes], storage_key: str) -> str:
        """Save file data to storage under the given key and return the key."""
        pass

    @abstractmethod
    def retrieve(self, storage_key: str) -> Optional[bytes]:
        """Retrieve raw file bytes for the given storage key."""
        pass

    @abstractmethod
    def delete(self, storage_key: str) -> bool:
        """Delete file associated with storage key."""
        pass

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        """Check if file exists for storage key."""
        pass

    @abstractmethod
    def get_local_path(self, storage_key: str) -> Optional[str]:
        """Return local filepath if applicable (e.g. for local storage), or None."""
        pass


class LocalStorageService(StorageService):
    """Local filesystem storage implementation for development and testing."""

    def __init__(self, base_folder: Union[str, Path]):
        self.base_folder = Path(base_folder)
        self.base_folder.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, storage_key: str) -> Path:
        # Prevent directory traversal attacks
        clean_key = storage_key.replace('..', '').strip('/\\')
        return self.base_folder / clean_key

    def save(self, file_data: Union[FileStorage, BinaryIO, bytes], storage_key: str) -> str:
        target_path = self._resolve_path(storage_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(file_data, FileStorage):
            file_data.save(str(target_path))
        elif isinstance(file_data, bytes):
            with open(target_path, 'wb') as f:
                f.write(file_data)
        elif hasattr(file_data, 'read'):
            with open(target_path, 'wb') as f:
                shutil.copyfileobj(file_data, f)
        else:
            raise ValueError("Unsupported file_data type provided to LocalStorageService.save")

        return storage_key

    def retrieve(self, storage_key: str) -> Optional[bytes]:
        target_path = self._resolve_path(storage_key)
        if not target_path.is_file():
            return None
        with open(target_path, 'rb') as f:
            return f.read()

    def delete(self, storage_key: str) -> bool:
        target_path = self._resolve_path(storage_key)
        if target_path.is_file():
            target_path.unlink()
            return True
        return False

    def exists(self, storage_key: str) -> bool:
        target_path = self._resolve_path(storage_key)
        return target_path.is_file()

    def get_local_path(self, storage_key: str) -> Optional[str]:
        target_path = self._resolve_path(storage_key)
        if target_path.is_file():
            return str(target_path)
        return None
