import os

from django.conf import settings

from core.constant import StorageBackendEnum
from core.services.storage.base import StorageBackend


class S3StorageBackend(StorageBackend):
    def __init__(self):
        import boto3
        from botocore.config import Config

        self.bucket = settings.AWS_STORAGE_BUCKET_NAME
        self.client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=getattr(settings, "AWS_S3_REGION_NAME", None),
            endpoint_url=getattr(settings, "AWS_S3_ENDPOINT_URL", None),
            config=Config(signature_version="s3v4"),
        )

    def save(self, source_path: str, storage_key: str) -> None:
        with open(source_path, "rb") as handle:
            self.client.upload_fileobj(handle, self.bucket, storage_key)

    def delete(self, storage_key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=storage_key)

    def exists(self, storage_key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=storage_key)
            return True
        except self.client.exceptions.ClientError:
            return False

    def get_url(self, storage_key: str) -> str:
        custom_domain = getattr(settings, "AWS_S3_CUSTOM_DOMAIN", "")
        if custom_domain:
            return f"https://{custom_domain}/{storage_key}"
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": storage_key},
            ExpiresIn=getattr(settings, "AWS_S3_URL_EXPIRE_SECONDS", 3600),
        )

    def backend_type(self) -> int:
        endpoint = getattr(settings, "AWS_S3_ENDPOINT_URL", "") or ""
        if "minio" in endpoint.lower():
            return StorageBackendEnum.MINIO.value
        return StorageBackendEnum.S3.value
