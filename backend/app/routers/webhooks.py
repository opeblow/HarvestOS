from __future__ import annotations

from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, HTTPException, Query, Request

from app.config import settings
from app.services.journey import get_journey
from app.shared import Message

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/sms")
async def sms_inbound(request: Request, auth: str = Query(default="")) -> dict:
    if auth != settings.sms_webhook_auth_token:
        raise HTTPException(status_code=401, detail="invalid webhook token")
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = await request.json()
    else:
        form = await request.form()
        payload = dict(form)

    sender = payload.get("from") or payload.get("originationPhoneNumber")
    body = payload.get("body") or payload.get("messageBody") or ""
    if not sender:
        raise HTTPException(status_code=400, detail="missing sender number")
    message = Message(channel="sms", from_number=sender, body=body)
    receipts = get_journey().handle_inbound(message)
    return {"status": "ok", "delivered": [r.model_dump() for r in receipts]}


@router.get("/whatsapp")
def whatsapp_verify(
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
) -> Any:
    if hub_verify_token == settings.whatsapp_verify_token and hub_challenge:
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="verification failed")


@router.post("/whatsapp")
async def whatsapp_inbound(request: Request) -> dict:
    payload = await request.json()
    messages = _extract_whatsapp_messages(payload)
    for message in messages:
        strategy = get_journey()
        strategy.handle_inbound(message)
    return {"status": "ok"}


@router.post("/ses")
async def ses_notification(request: Request) -> dict:
    payload = await request.json()
    message_type = payload.get("Type", "")
    if message_type == "SubscriptionConfirmation":
        return {"status": "subscribed"}
    return {"status": "ok", "notification": message_type}


def _extract_whatsapp_messages(payload: dict) -> list[Message]:
    out: list[Message] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for value in change.get("value", {}).get("messages", []):
                sender = value.get("from")
                if not sender:
                    continue
                message_id = value.get("id", "")
                message_type = value.get("type", "text")
                if message_type == "image":
                    media_id = value.get("image", {}).get("id", "")
                    out.append(
                        Message(
                            channel="whatsapp",
                            from_number=sender,
                            body="[photo uploaded]",
                            media_url=_resolve_media(media_id),
                            message_id=message_id,
                        )
                    )
                else:
                    text = (value.get("text") or {}).get("body", "")
                    out.append(
                        Message(
                            channel="whatsapp",
                            from_number=sender,
                            body=text,
                            message_id=message_id,
                        )
                    )
    return out


def _resolve_media(media_id: str) -> str:
    if not media_id:
        return ""
    # Downloading WhatsApp media requires the optional EUM Social provider and S3
    # asset storage. Without them the journey still records a local reference.
    if not settings.whatsapp_enabled or not settings.asset_storage_is_s3:
        return f"media://{media_id}"
    try:
        client = boto3.client("socialmessaging", region_name=settings.region)
        key = f"photos/{media_id}.jpg"
        client.get_whatsapp_message_media(
            mediaId=media_id,
            originationPhoneNumberId=settings.whatsapp_phone_number_id,
            destinationS3File={"bucketName": settings.asset_bucket, "key": key},
        )
        return f"s3://{settings.asset_bucket}/{key}"
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(status_code=502, detail=f"media download failed: {exc}") from exc
