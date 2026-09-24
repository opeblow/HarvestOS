from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.config import CHANNEL_SMS


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


class ProviderError(RuntimeError):
    """Raised when an optional external provider is misconfigured or unavailable."""


CATEGORY_DIAGNOSIS = "diagnosis"
CATEGORY_COMMERCE = "commerce"
CATEGORY_FINANCE = "finance"
CATEGORY_LOGISTICS = "logistics"
CATEGORY_SYSTEM = "system"


class Message(BaseModel):
    channel: str
    from_number: str
    body: str = ""
    media_url: str = ""
    message_id: str = Field(default_factory=lambda: uuid4().hex)
    ts: str = Field(default_factory=utcnow)

    @property
    def has_media(self) -> bool:
        return bool(self.media_url)


class Session(BaseModel):
    phone_number: str
    session_id: str = Field(default_factory=lambda: uuid4().hex)
    channel: str = CHANNEL_SMS
    visited_channels: list[str] = Field(default_factory=list)
    conversation: list[Message] = Field(default_factory=list)
    state: dict[str, Any] = Field(default_factory=dict)
    created_ts: str = Field(default_factory=utcnow)
    updated_ts: str = Field(default_factory=utcnow)

    def touch(self) -> None:
        self.updated_ts = utcnow()


class ChannelCapability(BaseModel):
    channel: str
    text: bool = True
    buttons: bool = False
    media: bool = False


CHANNEL_CAPABILITIES: dict[str, ChannelCapability] = {
    "sms": ChannelCapability(channel="sms", text=True),
    "whatsapp": ChannelCapability(channel="whatsapp", text=True, media=True),
    "rcs": ChannelCapability(channel="rcs", text=True, buttons=True),
    "email": ChannelCapability(channel="email", text=True),
}


class RcsButton(BaseModel):
    title: str
    action: str = "postback"
    postback_data: str


class RcsCard(BaseModel):
    title: str
    description: str = ""
    media_url: str = ""
    buttons: list[RcsButton] = Field(default_factory=list)


class Escalation(BaseModel):
    channel: str
    reason: str
    payload: dict[str, Any] = Field(default_factory=dict)


class DiagnosisResult(BaseModel):
    crop: str = "maize"
    issue: str = ""
    confidence: float = 0.0
    plain_language: str = ""
    recommendation: str = ""
    agent: str = "diagnosis"


class ProductQuote(BaseModel):
    sku: str
    product: str
    price_ngn: float
    dealer: str
    dealer_distance_km: float
    stock: int


class LoanPlan(BaseModel):
    amount_ngn: float
    installments: int
    per_payment_ngn: float
    agreement_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    terms: str = ""


class OutboundMessage(BaseModel):
    channel: str
    to: str
    text: str = ""
    card: RcsCard | None = None
    media_url: str = ""
    email_type: str = "text"
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    category: str = "system"
    entity: dict[str, Any] = Field(default_factory=dict)


class SendReceipt(BaseModel):
    channel: str
    to: str
    text: str = ""
    message_id: str = Field(default_factory=lambda: uuid4().hex)
    provider: str = "memory"
    delivered: bool = True


class ConversationTurn(BaseModel):
    intent: str = ""
    agent: str = ""
    reply_text: str = ""
    escalation: Escalation | None = None
    card: RcsCard | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class JourneyPlan(BaseModel):
    outbound: list[OutboundMessage] = Field(default_factory=list)
    session: Session
    trace: list[ConversationTurn] = Field(default_factory=list)
