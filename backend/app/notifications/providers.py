from __future__ import annotations

from app.channels.base import ChannelAdapter
from app.config import CHANNEL_IN_APP
from app.notifications.base import (
    CATEGORY_SYSTEM,
    CATEGORY_TITLES,
    Notification,
    NotificationProvider,
)
from app.notifications.store import NotificationStore
from app.shared import OutboundMessage, ProviderError, SendReceipt


class InAppNotificationProvider(NotificationProvider):
    """Core provider: records every notification in the HarvestOS inbox."""

    name = "in_app"
    channel = CHANNEL_IN_APP

    def __init__(self, store: NotificationStore) -> None:
        self._store = store

    def build(self, message: OutboundMessage) -> Notification:
        category = message.category or CATEGORY_SYSTEM
        return Notification(
            recipient=message.to,
            channel=message.channel,
            category=category,
            title=CATEGORY_TITLES.get(category, CATEGORY_TITLES[CATEGORY_SYSTEM]),
            body=message.text,
            entity=dict(message.entity),
        )

    def deliver(self, message: OutboundMessage) -> SendReceipt:
        self._store.create(self.build(message))
        return SendReceipt(
            channel=message.channel,
            to=message.to,
            text=message.text,
            provider=self.name,
            delivered=True,
        )


class ChannelNotificationProvider(NotificationProvider):
    """Optional provider that delivers through a configured channel adapter."""

    def __init__(self, name: str, channel: str, adapter: ChannelAdapter) -> None:
        self.name = name
        self.channel = channel
        self._adapter = adapter

    def deliver(self, message: OutboundMessage) -> SendReceipt:
        return self._adapter.send(message)


class DisabledNotificationProvider(NotificationProvider):
    """Placeholder for an optional provider that has not been enabled.

    Delivering through a disabled provider raises a clear configuration error
    rather than silently pretending an external message was sent.
    """

    def __init__(self, name: str, channel: str) -> None:
        self.name = name or "disabled"
        self.channel = channel

    def deliver(self, message: OutboundMessage) -> SendReceipt:
        raise ProviderError(
            f"{self.channel} provider is disabled; enable it and provide its configuration "
            "to send external messages"
        )
