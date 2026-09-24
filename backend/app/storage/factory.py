from __future__ import annotations

from app.config import Settings, settings
from app.storage.base import AssetStorage
from app.storage.local import LocalAssetStorage
from app.storage.s3 import S3AssetStorage


class AssetStorageFactory:
    @staticmethod
    def create(config: Settings) -> AssetStorage:
        if config.asset_storage_is_s3:
            return S3AssetStorage(config.asset_bucket, config.region)
        return LocalAssetStorage(config.asset_local_dir)


_storage: AssetStorage | None = None


def get_asset_storage() -> AssetStorage:
    global _storage
    if _storage is None:
        _storage = AssetStorageFactory.create(settings)
    return _storage


def load_ref(ref: str) -> bytes:
    """Load an asset from any reference the active storage can resolve."""
    if not ref:
        raise ValueError("empty asset reference")
    return get_asset_storage().load(ref)
