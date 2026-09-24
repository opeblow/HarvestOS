from __future__ import annotations

from app.shared import CHANNEL_CAPABILITIES, ChannelCapability, Session

TASK_MEDIA_CAPTURE = "media_capture"
TASK_DECISION_CARD = "decision_card"
TASK_DOCUMENT = "document"
TASK_TEXT = "text"


def capabilities_for(channel: str) -> ChannelCapability:
    return CHANNEL_CAPABILITIES.get(channel, CHANNEL_CAPABILITIES["sms"])


def pick_channel(session: Session, task: str) -> str:
    if task == TASK_MEDIA_CAPTURE:
        return "whatsapp"
    if task == TASK_DECISION_CARD:
        return "rcs"
    if task == TASK_DOCUMENT:
        return "email"
    return session.channel if session.channel else "sms"
