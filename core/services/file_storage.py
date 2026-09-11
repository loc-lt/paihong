import hashlib
import mimetypes
import os
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from core.models import FileObject
from core.services.storage import get_storage_backend
from core.services.storage.local import LocalStorageBackend


def compute_sha256(file_path: str) -> str:
    digest = hashlib.sha256()
    with open(file_path, "rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_storage_key(sha256: str, extension: str) -> str:
    ext = extension.lower().lstrip(".")
    suffix = f".{ext}" if ext else ""
    return f"objects/{sha256[:2]}/{sha256}{suffix}"


def get_file_url(storage_key: str, storage_backend=None) -> str:
    backend = get_storage_backend(storage_backend)
    return backend.get_url(storage_key)


def find_existing_file_object(sha256: str, size_bytes: int):
    return FileObject.objects.filter(sha256=sha256, size_bytes=size_bytes).first()


def _reuse_existing_file_object(existing: FileObject, *, source_path: str) -> FileObject:
    backend = get_storage_backend(existing.storage_backend)
    if backend.exists(existing.storage_key):
        return existing
    backend.save(source_path, existing.storage_key)
    return existing


@transaction.atomic
def store_uploaded_file(uploaded_file: UploadedFile, *, created_by=None) -> FileObject:
    backend = get_storage_backend()
    extension = Path(uploaded_file.name).suffix.lstrip(".").lower()
    mime_type = uploaded_file.content_type or mimetypes.guess_type(uploaded_file.name)[0] or ""

    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        for chunk in uploaded_file.chunks():
            temp_file.write(chunk)
        temp_path = temp_file.name

    try:
        sha256 = compute_sha256(temp_path)
        size_bytes = os.path.getsize(temp_path)
        existing = find_existing_file_object(sha256, size_bytes)
        if existing:
            result = _reuse_existing_file_object(existing, source_path=temp_path)
            return result

        storage_key = build_storage_key(sha256, extension)
        backend.save(temp_path, storage_key)

        return FileObject.objects.create(
            storage_backend=backend.backend_type(),
            storage_key=storage_key,
            extension=extension,
            mime_type=mime_type,
            size_bytes=size_bytes,
            sha256=sha256,
            created_by=created_by,
        )
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def store_file_from_path(
    file_path: str,
    *,
    original_filename: str,
    created_by=None,
) -> FileObject:
    backend = get_storage_backend()
    extension = Path(original_filename).suffix.lstrip(".").lower()
    mime_type = mimetypes.guess_type(original_filename)[0] or ""
    sha256 = compute_sha256(file_path)
    size_bytes = os.path.getsize(file_path)

    existing = find_existing_file_object(sha256, size_bytes)
    if existing:
        return _reuse_existing_file_object(existing, source_path=file_path)

    storage_key = build_storage_key(sha256, extension)
    backend.save(file_path, storage_key)

    return FileObject.objects.create(
        storage_backend=backend.backend_type(),
        storage_key=storage_key,
        extension=extension,
        mime_type=mime_type,
        size_bytes=size_bytes,
        sha256=sha256,
        created_by=created_by,
    )


def delete_file_object(file_object: FileObject) -> None:
    backend = get_storage_backend(file_object.storage_backend)
    backend.delete(file_object.storage_key)


def read_file_object_bytes(file_object: FileObject) -> bytes:
    backend = get_storage_backend(file_object.storage_backend)
    if isinstance(backend, LocalStorageBackend):
        return backend._absolute_path(file_object.storage_key).read_bytes()
    raise NotImplementedError(
        "Reading file bytes is only supported for local storage backend."
    )


def store_bytes_content(
    content: bytes,
    *,
    filename: str,
    created_by=None,
) -> FileObject:
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(content)
        temp_path = temp_file.name
    try:
        return store_file_from_path(
            temp_path,
            original_filename=filename,
            created_by=created_by,
        )
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
