from __future__ import annotations

from app.channels.factory import ChannelRegistry, registry
from app.config import DISABLED_PROVIDER, IN_APP_PROVIDER, settings
from app.notifications.base import Notification
from app.notifications.providers import (
    ChannelNotificationProvider,
    DisabledNotificationProvider,
    InAppNotificationProvider,
)
from app.notifications.store import NotificationStore, NotificationStoreFactory
from app.shared import OutboundMessage, ProviderError, SendReceipt


class NotificationService:
    """Routes outbound messages to the in-app inbox and optional providers.

    The in-app inbox is always written first, so a notification is never lost
    because an external channel is unavailable. External delivery is attempted
    only when that channel's provider has been explicitly enabled.
    """

    def __init__(self, store: NotificationStore, registry: ChannelRegistry) -> None:
        self.store = store
        self.registry = registry
        self.in_app = InAppNotificationProvider(store)
        self._providers = self._build_providers(registry)

    @staticmethod
    def _build_providers(registry: ChannelRegistry) -> dict[str, object]:
        providers: dict[str, object] = {}
        for channel, provider_name in settings.external_channels.items():
            if provider_name == DISABLED_PROVIDER:
                providers[channel] = DisabledNotificationProvider(provider_name, channel)
            else:
                providers[channel] = ChannelNotificationProvider(
                    provider_name, channel, registry.dispatch(channel)
                )
        return providers

    def deliver(self, message: OutboundMessage) -> SendReceipt:
        provider = self._providers.get(message.channel)
        external: SendReceipt | None = None
        if isinstance(provider, ChannelNotificationProvider):
            try:
                external = provider.deliver(message)
            except ProviderError:
                raise
            except Exception:  # noqa: BLE001 - external failures must not break the core flow
                external = SendReceipt(
                    channel=message.channel,
                    to=message.to,
                    text=message.text,
                    provider=provider.name,
                    delivered=False,
                )

        notification = self.in_app.build(message)
        if external is not None:
            notification.delivered_externally = external.delivered
            notification.external_provider = external.provider
        self.store.create(notification)

        if external is not None:
            return external
        return SendReceipt(
            channel=message.channel,
            to=message.to,
            text=message.text,
            provider=IN_APP_PROVIDER,
            delivered=True,
        )

    def list(
        self,
        recipient: str | None = None,
        limit: int = 100,
        unread_only: bool = False,
    ) -> list[Notification]:
        return self.store.list(recipient=recipient, limit=limit, unread_only=unread_only)

    def mark_read(self, notification_id: str) -> Notification | None:
        return self.store.mark_read(notification_id)

    def unread_count(self, recipient: str | None = None) -> int:
        return self.store.unread_count(recipient=recipient)


_service: NotificationService | None = None


def get_notification_service() -> NotificationService:
    global _service
    if _service is None:
        _service = NotificationService(NotificationStoreFactory.create(settings), registry)
    return _service
