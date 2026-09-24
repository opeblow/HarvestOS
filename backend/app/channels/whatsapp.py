from __future__ import annotations

import json

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.channels.base import ChannelAdapter
from app.config import settings
from app.shared import OutboundMessage, SendReceipt

META_API_VERSION = "v19.0"


class WhatsAppAdapter(ChannelAdapter):
    """AWS End User Messaging Social (WhatsApp) — verified SDK: socialmessaging."""

    provider = "aws-eum-social"

    def __init__(self) -> None:
        self._client = boto3.client("socialmessaging", region_name=settings.region)

    def send(self, message: OutboundMessage) -> SendReceipt:
        if not settings.whatsapp_phone_number_id:
            raise RuntimeError("WhatsApp send requires WHATSAPP_PHONE_NUMBER_ID (EUM Social)")
        try:
            if message.media_url:
                media_id = self._post_media(message.media_url)
                payload = {
                    "messaging_product": "whatsapp",
                    "to": message.to,
                    "type": "image",
                    "image": {"id": media_id, "caption": message.text},
                }
            else:
                payload = {
                    "messaging_product": "whatsapp",
                    "to": message.to,
                    "type": "text",
                    "text": {"body": message.text},
                }
            self._client.send_whatsapp_message(
                originationPhoneNumberId=settings.whatsapp_phone_number_id,
                message=json.dumps(payload),
                metaApiVersion=META_API_VERSION,
            )
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError(f"EUM Social WhatsApp send failed: {exc}") from exc
        return SendReceipt(
            channel=message.channel,
            to=message.to,
            text=message.text,
            provider=self.provider,
        )

    def _post_media(self, media_url: str) -> str:
        resp = self._client.post_whatsapp_message_media(
            originationPhoneNumberId=settings.whatsapp_phone_number_id,
            sourceS3PresignedUrl=media_url,
        )
        return resp["mediaId"]
