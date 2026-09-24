from __future__ import annotations

from abc import ABC, abstractmethod


class AssetStorage(ABC):
    """Object storage for non-core assets (crop photos, generated documents).

    The core product does not require durable object storage: local storage is
    the development default and S3 is an optional production adapter.
    """

    scheme: str

    @abstractmethod
    def save(self, key: str, data: bytes, content_type: str = "") -> str:
        """Persist bytes under ``key`` and return a stable reference."""

    @abstractmethod
    def load(self, ref: str) -> bytes:
        """Read bytes for a reference previously returned by :meth:`save`."""

    def url(self, ref: str, expires: int = 900) -> str:
        """Return a retrievable URL/reference. Local storage returns the ref."""
        return ref
