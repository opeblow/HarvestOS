from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.shared import (
    CATEGORY_COMMERCE,
    CATEGORY_DIAGNOSIS,
    CATEGORY_FINANCE,
    CATEGORY_LOGISTICS,
    CATEGORY_SYSTEM,
    utcnow,
)

CATEGORY_TITLES: dict[str, str] = {
    CATEGORY_DIAGNOSIS: "Crop assessment",
    CATEGORY_COMMERCE: "Input availability",
    CATEGORY_FINANCE: "Payment plan",
    CATEGORY_LOGISTICS: "Pickup update",
    CATEGORY_SYSTEM: "HarvestOS update",
}


class Notification(BaseModel):
    """A durable, in-app notification stored by the HarvestOS backend.

    The in-app inbox is the core delivery mechanism: every user-facing update is
    recorded here regardless of whether an optional external channel is enabled.
    """

    id: str = Field(default_factory=lambda: uuid4().hex)
    recipient: str = ""
    channel: str = "in_app"
    category: str = CATEGORY_SYSTEM
    title: str = ""
    body: str = ""
    entity: dict[str, Any] = Field(default_factory=dict)
    created_ts: str = Field(default_factory=utcnow)
    read_ts: str | None = None
    delivered_externally: bool = False
    external_provider: str = ""

    @property
    def read(self) -> bool:
        return self.read_ts is not None


class NotificationProvider(ABC):
    """A delivery mechanism for notifications."""

    name: str

    @abstractmethod
    def deliver(self, notification: Notification) -> bool: ...
