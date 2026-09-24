from __future__ import annotations

from app.channels.base import ChannelAdapter, DisabledAdapter
from app.channels.email import SESEmailAdapter
from app.channels.sms_rcs import SmsRcsAdapter
from app.channels.whatsapp import WhatsAppAdapter
from app.config import settings


class ChannelRegistry:
    """Builds only the external adapters whose providers are explicitly enabled.

    Disabled channels resolve to a :class:`DisabledAdapter` that fails with a
    clear configuration error, so the core application never depends on an
    unavailable provider and never silently pretends a message was delivered.
    """

    def __init__(self) -> None:
        self.sms: ChannelAdapter = (
            SmsRcsAdapter() if settings.sms_enabled else DisabledAdapter("sms")
        )
        self.whatsapp: ChannelAdapter = (
            WhatsAppAdapter() if settings.whatsapp_enabled else DisabledAdapter("whatsapp")
        )
        self.email: ChannelAdapter = (
            SESEmailAdapter() if settings.email_enabled else DisabledAdapter("email")
        )

    def dispatch(self, channel: str) -> ChannelAdapter:
        return {
            "sms": self.sms,
            "rcs": self.sms,
            "whatsapp": self.whatsapp,
            "email": self.email,
        }[channel]


registry = ChannelRegistry()
