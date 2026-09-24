from __future__ import annotations

from abc import ABC, abstractmethod

from app.shared import OutboundMessage, ProviderError, SendReceipt

from ..config import settings


class ChannelAdapter(ABC):
    provider: str

    @abstractmethod
    def send(self, message: OutboundMessage) -> SendReceipt: ...


class DisabledAdapter(ChannelAdapter):
    """Adapter placeholder for an external channel that is not enabled.

    Sending raises a clear configuration error so a disabled channel can never
    be mistaken for a delivered message.
    """

    provider = "disabled"

    def __init__(self, channel: str) -> None:
        self._channel = channel

    def send(self, message: OutboundMessage) -> SendReceipt:
        raise ProviderError(
            f"{self._channel} channel is disabled; enable its provider and configuration "
            "to send external messages"
        )


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
