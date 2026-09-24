from __future__ import annotations

import logging

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.channels.base import ChannelAdapter
from app.config import settings
from app.shared import OutboundMessage, RcsCard, SendReceipt

logger = logging.getLogger(__name__)

RCS_MESSAGE_TEMPLATE = {
    "content": {
        "standaloneCard": {
            "cardContent": {
                "media": {"mediaUrl": None},
                "description": None,
                "title": None,
                "suggestedActions": [],
            }
        }
    }
}


class SmsRcsAdapter(ChannelAdapter):
    """AWS End User Messaging (SMS + RCS) — verified SDK service: pinpoint-sms-voice-v2.

    RCS is best-effort: if it fails (or the platform is unreachable), the message
    degrades to a plain SMS so a farmer is never left without an answer.
    """

    provider = "aws-eum"

    def __init__(self) -> None:
        self._client = boto3.client("pinpoint-sms-voice-v2", region_name=settings.region)

    def send(self, message: OutboundMessage) -> SendReceipt:
        if not settings.sms_origination_identity:
            raise RuntimeError(
                "SMS/RCS send requires SMS_ORIGINATION_IDENTITY (CDS sandbox number)"
            )
        sent_via = "sms"
        try:
            if message.channel == "rcs" and message.card:
                self._send_rcs_card(message)
                sent_via = "rcs"
            else:
                self._send_sms(message.text, message.to)
        except (BotoCoreError, ClientError) as exc:
            logger.warning("RCS/SMS primary send failed, falling back to SMS: %s", exc)
            fallback = (
                message.text if message.card is None else (message.card.title or message.text)
            )
            self._send_sms(fallback, message.to)
            sent_via = "sms-fallback"
        return SendReceipt(
            channel=message.channel,
            to=message.to,
            text=message.text or (message.card.title if message.card else ""),
            provider=f"{self.provider}:{sent_via}",
        )

    def _send_sms(self, text: str, to: str) -> None:
        self._client.send_text_message(
            DestinationPhoneNumber=to,
            OriginationIdentity=settings.sms_origination_identity,
            MessageBody=text,
        )

    def _send_rcs_card(self, message: OutboundMessage) -> None:
        card: RcsCard | None = message.card
        if card is None:
            self._send_sms(message.text, message.to)
            return
        payload = dict(RCS_MESSAGE_TEMPLATE)
        payload["content"]["standaloneCard"]["cardContent"]["title"] = card.title
        payload["content"]["standaloneCard"]["cardContent"]["description"] = card.description
        payload["content"]["standaloneCard"]["cardContent"]["media"]["mediaUrl"] = card.media_url
        payload["content"]["standaloneCard"]["cardContent"]["suggestedActions"] = [
            {
                "title": btn.title,
                "postbackData": btn.postback_data,
                "action": "reply",
                "replyQuery": btn.postback_data,
            }
            for btn in card.buttons
            if btn.action == "postback"
        ]
        self._client.send_rcs_message(
            DestinationPhoneNumber=message.to,
            OriginationIdentity=settings.sms_origination_identity,
            RcsMessageContent=payload,
        )
