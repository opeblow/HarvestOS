from __future__ import annotations

import json
from abc import ABC, abstractmethod

import boto3
from botocore.exceptions import ClientError

from app.config import Settings
from app.notifications.base import Notification
from app.shared import utcnow

SYSTEM_PARTITION = "system"
NOTIFICATION_PREFIX = "notif#"


class NotificationStore(ABC):
    @abstractmethod
    def create(self, notification: Notification) -> Notification: ...

    @abstractmethod
    def update(self, notification: Notification) -> Notification: ...

    @abstractmethod
    def get(self, notification_id: str) -> Notification | None: ...

    @abstractmethod
    def list(
        self,
        recipient: str | None = None,
        limit: int = 100,
        unread_only: bool = False,
    ) -> list[Notification]: ...

    @abstractmethod
    def mark_read(self, notification_id: str) -> Notification | None: ...

    def unread_count(self, recipient: str | None = None) -> int:
        return sum(1 for n in self.list(recipient=recipient, limit=1000, unread_only=True))


class InMemoryNotificationStore(NotificationStore):
    def __init__(self) -> None:
        self._store: dict[str, Notification] = {}

    def create(self, notification: Notification) -> Notification:
        self._store[notification.id] = notification
        return notification

    def update(self, notification: Notification) -> Notification:
        self._store[notification.id] = notification
        return notification

    def get(self, notification_id: str) -> Notification | None:
        return self._store.get(notification_id)

    def list(
        self,
        recipient: str | None = None,
        limit: int = 100,
        unread_only: bool = False,
    ) -> list[Notification]:
        items = list(self._store.values())
        if recipient is not None:
            items = [n for n in items if n.recipient == recipient]
        if unread_only:
            items = [n for n in items if not n.read]
        items.sort(key=lambda n: n.created_ts, reverse=True)
        return items[:limit]

    def mark_read(self, notification_id: str) -> Notification | None:
        notification = self._store.get(notification_id)
        if notification is None:
            return None
        if notification.read_ts is None:
            notification.read_ts = utcnow()
        return notification


class DynamoDBNotificationStore(NotificationStore):
    def __init__(self, settings: Settings) -> None:
        region = settings.region
        self._table = boto3.resource("dynamodb", region_name=region).Table(settings.table_name)

    @staticmethod
    def _key(notification: Notification) -> dict[str, str]:
        return {
            "pk": notification.recipient or SYSTEM_PARTITION,
            "sk": f"{NOTIFICATION_PREFIX}{notification.created_ts}#{notification.id}",
        }

    def create(self, notification: Notification) -> Notification:
        try:
            self._table.put_item(
                Item={**self._key(notification), "document": notification.model_dump_json()}
            )
        except ClientError as exc:
            raise RuntimeError("failed to persist notification") from exc
        return notification

    def update(self, notification: Notification) -> Notification:
        return self.create(notification)

    def get(self, notification_id: str) -> Notification | None:
        for item in self._scan():
            notification = Notification.model_validate(json.loads(item["document"]))
            if notification.id == notification_id:
                return notification
        return None

    def list(
        self,
        recipient: str | None = None,
        limit: int = 100,
        unread_only: bool = False,
    ) -> list[Notification]:
        notifications = [
            Notification.model_validate(json.loads(item["document"]))
            for item in self._scan()
            if item.get("sk", "").startswith(NOTIFICATION_PREFIX)
        ]
        if recipient is not None:
            notifications = [n for n in notifications if n.recipient == recipient]
        if unread_only:
            notifications = [n for n in notifications if not n.read]
        notifications.sort(key=lambda n: n.created_ts, reverse=True)
        return notifications[:limit]

    def mark_read(self, notification_id: str) -> Notification | None:
        for item in self._scan():
            notification = Notification.model_validate(json.loads(item["document"]))
            if notification.id != notification_id:
                continue
            if notification.read_ts is None:
                notification.read_ts = utcnow()
                self.update(notification)
            return notification
        return None

    def _scan(self) -> list[dict]:
        resp = self._table.scan()
        return resp.get("Items", [])


class NotificationStoreFactory:
    @staticmethod
    def create(settings: Settings) -> NotificationStore:
        if settings.storage_is_aws:
            return DynamoDBNotificationStore(settings)
        return InMemoryNotificationStore()
