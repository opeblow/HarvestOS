from __future__ import annotations

from urllib.parse import urlparse

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.storage.base import AssetStorage

S3_SCHEME = "s3"


class S3AssetStorage(AssetStorage):
    """Optional production storage backed by the encrypted HarvestOS asset bucket."""

    scheme = S3_SCHEME

    def __init__(self, bucket: str, region: str) -> None:
        self._bucket = bucket
        self._client = boto3.client("s3", region_name=region)

    def save(self, key: str, data: bytes, content_type: str = "") -> str:
        extra = {"ContentType": content_type} if content_type else {}
        try:
            self._client.put_object(Bucket=self._bucket, Key=key, Body=data, **extra)
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError(f"S3 asset upload failed: {exc}") from exc
        return f"{S3_SCHEME}://{self._bucket}/{key}"

    def load(self, ref: str) -> bytes:
        parsed = urlparse(ref)
        try:
            response = self._client.get_object(Bucket=parsed.netloc, Key=parsed.path.lstrip("/"))
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError(f"S3 asset download failed: {exc}") from exc
        return response["Body"].read()

    def url(self, ref: str, expires: int = 900) -> str:
        parsed = urlparse(ref)
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": parsed.netloc, "Key": parsed.path.lstrip("/")},
            ExpiresIn=expires,
        )
