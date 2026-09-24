from __future__ import annotations

from abc import ABC, abstractmethod

from app.shared import OutboundMessage, SendReceipt

from ..config import settings


class ChannelAdapter(ABC):
    provider: str

    @abstractmethod
    def send(self, message: OutboundMessage) -> SendReceipt: ...


class LoggingAdapter(ChannelAdapter):
    provider = "memory"

    def __init__(self, prefix: str = "channel") -> None:
        self._prefix = prefix

    def send(self, message: OutboundMessage) -> SendReceipt:
        if settings.app_env == "dev":
            print(
                f"[{self._prefix}] to={message.to} channel={message.channel} text={message.text!r}"
            )
        return SendReceipt(
            channel=message.channel,
            to=message.to,
            text=message.text,
            provider=self.provider,
        )
