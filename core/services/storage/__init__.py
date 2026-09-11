from django.conf import settings

from core.constant import StorageBackendEnum
from core.services.storage.base import StorageBackend
from core.services.storage.local import LocalStorageBackend
from core.services.storage.s3 import S3StorageBackend

_BACKENDS = {
    StorageBackendEnum.LOCAL.value: LocalStorageBackend,
    StorageBackendEnum.S3.value: S3StorageBackend,
    StorageBackendEnum.MINIO.value: S3StorageBackend,
    StorageBackendEnum.NAS.value: LocalStorageBackend,
}


def get_storage_backend(backend_type: int | None = None) -> StorageBackend:
    if backend_type is None:
        backend_type = getattr(
            settings,
            "OBJECT_STORAGE_BACKEND",
            StorageBackendEnum.LOCAL.value,
        )
    backend_cls = _BACKENDS.get(backend_type, LocalStorageBackend)
    return backend_cls()
