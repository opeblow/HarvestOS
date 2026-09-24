from __future__ import annotations

from app.channels.base import ChannelAdapter, LoggingAdapter
from app.channels.email import SESEmailAdapter
from app.channels.sms_rcs import SmsRcsAdapter
from app.channels.whatsapp import WhatsAppAdapter
from app.config import settings


class ChannelRegistry:
    def __init__(self) -> None:
        aws = settings.storage_is_aws
        self.sms: ChannelAdapter = SmsRcsAdapter() if aws else LoggingAdapter("sms")
        self.whatsapp: ChannelAdapter = WhatsAppAdapter() if aws else LoggingAdapter("whatsapp")
        self.email: ChannelAdapter = SESEmailAdapter() if aws else LoggingAdapter("email")

    def dispatch(self, channel: str):
        return {
            "sms": self.sms,
            "rcs": self.sms,
            "whatsapp": self.whatsapp,
            "email": self.email,
        }[channel]


registry = ChannelRegistry()
