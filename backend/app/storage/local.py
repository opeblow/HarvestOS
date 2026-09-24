from __future__ import annotations

from pathlib import Path

from app.storage.base import AssetStorage

LOCAL_SCHEME = "local"


class LocalAssetStorage(AssetStorage):
    """Development/default storage: files under a local, git-ignored directory."""

    scheme = LOCAL_SCHEME

    def __init__(self, base_dir: str) -> None:
        self._base = Path(base_dir)

    def save(self, key: str, data: bytes, content_type: str = "") -> str:
        path = self._base / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return f"{LOCAL_SCHEME}://{key}"

    def load(self, ref: str) -> bytes:
        key = ref[len(f"{LOCAL_SCHEME}://") :] if ref.startswith(f"{LOCAL_SCHEME}://") else ref
        return (self._base / key).read_bytes()
