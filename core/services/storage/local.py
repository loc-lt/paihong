import os
import shutil
from pathlib import Path

from django.conf import settings

from core.constant import StorageBackendEnum
from core.services.storage.base import StorageBackend


class LocalStorageBackend(StorageBackend):
    def _media_root(self) -> Path:
        return Path(getattr(settings, "FILE_STORAGE_ROOT", settings.MEDIA_ROOT))

    def _absolute_path(self, storage_key: str) -> Path:
        return self._media_root() / storage_key

    def save(self, source_path: str, storage_key: str) -> None:
        destination = self._absolute_path(storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if os.path.abspath(source_path) != os.path.abspath(destination):
            shutil.move(source_path, destination)
        os.chmod(destination, 0o644)

    def delete(self, storage_key: str) -> None:
        path = self._absolute_path(storage_key)
        if path.exists():
            path.unlink()

    def exists(self, storage_key: str) -> bool:
        return self._absolute_path(storage_key).exists()

    def get_url(self, storage_key: str) -> str:
        domain = getattr(settings, "BE_DOMAIN", "")
        media_url = getattr(settings, "MEDIA_URL", "/media/")
        if domain:
            return f"{domain}{media_url}{storage_key}"
        return f"{media_url}{storage_key}"

    def backend_type(self) -> int:
        return StorageBackendEnum.LOCAL.value
