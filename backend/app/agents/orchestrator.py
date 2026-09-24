from __future__ import annotations

import re

from app.agents.base import Agent
from app.agents.commerce import CommerceAgent
from app.agents.diagnosis import DiagnosisAgent
from app.agents.finance import FinanceAgent
from app.agents.logistics import LogisticsAgent
from app.config import CHANNEL_EMAIL, CHANNEL_RCS, CHANNEL_WHATSAPP
from app.shared import (
    ConversationTurn,
    JourneyPlan,
    Message,
    OutboundMessage,
    Session,
)

KYC_NAME_RE = re.compile(r"NAME\s+(.+?)(?:\s+STATE\s+|\s*$)", re.IGNORECASE)
KYC_STATE_RE = re.compile(r"STATE\s+([A-Za-z\s'-]+)", re.IGNORECASE)
RESERVE_RE = re.compile(r"RESERVE\s+(\S+)", re.IGNORECASE)


class Orchestrator:
    def __init__(
        self,
        diagnosis: Agent | None = None,
        commerce: Agent | None = None,
        finance: Agent | None = None,
        logistics: Agent | None = None,
    ) -> None:
        self.diagnosis = diagnosis or DiagnosisAgent()
        self.commerce = commerce or CommerceAgent()
        self.finance = finance or FinanceAgent()
        self.logistics = logistics or LogisticsAgent()

    def handle(self, session: Session, message: Message) -> JourneyPlan:
        self._capture_kyc(session, message)
        intent = self._classify(session)
        trace: list[ConversationTurn] = []

        if intent == "finance" or (
            session.state.get("finance_pending") and (session.state.get("kyc") or {}).get("name")
        ):
            turn = self.finance.run(session)
            trace.append(turn)
            return self._compose(session, message.channel, [turn])

        if intent == "photo_diagnosis":
            turn = self.diagnosis.run(session)
            trace.append(turn)
            session.state["diagnosis"] = turn.data.get("diagnosis", {})
            session.state["product_sku"] = "NPK151515"
            if "next_intent" in turn.data:
                quote_turn = self.commerce.run(session)
                trace.append(quote_turn)
                return self._compose(session, message.channel, trace)

            return self._compose(session, message.channel, [turn])

        if intent == "commerce":
            turn = self.commerce.run(session)
            trace.append(turn)
            return self._compose(session, message.channel, trace)

        if intent == "reserve":
            reserve = self._reserve(session, message)
            session.state["order_status"] = "reserved"
            session.state["reservation"] = reserve
            confirm = self.logistics.run(session)
            trace.append(confirm)
            return self._compose(session, message.channel, trace)

        if intent == "chitchat":
            turn = ConversationTurn(
                intent="chitchat",
                agent="orchestrator",
                reply_text=(
                    "I'm Ope's HarvestOS assistant for farmers. Describe a crop problem like "
                    "'maize leaves turning yellow', ask for a price check, or say FINANCE to "
                    "split a payment."
                ),
            )
            trace.append(turn)
            return self._compose(session, message.channel, trace)

        turn = self.diagnosis.run(session)
        trace.append(turn)
        return self._compose(session, message.channel, trace)

    def _compose(
        self, session: Session, current_channel: str, trace: list[ConversationTurn]
    ) -> JourneyPlan:
        outbound: list[OutboundMessage] = []
        for turn in trace:
            if turn.reply_text:
                outbound.append(
                    OutboundMessage(
                        channel=current_channel,
                        to=session.phone_number,
                        text=turn.reply_text,
                    )
                )
            if not turn.escalation:
                continue
            esc = turn.escalation
            payload = esc.payload or {}
            if esc.channel == CHANNEL_WHATSAPP:
                link = "https://wa.me/[PENDING_NUMBER]?text=Hi%20HarvestOS"
                text = (
                    f"Send a clear close-up photo of the affected leaves: {link} "
                    "(message the same number on WhatsApp)"
                )
                outbound.append(
                    OutboundMessage(channel=CHANNEL_WHATSAPP, to=session.phone_number, text=text)
                )
            elif esc.channel == CHANNEL_RCS or turn.card or payload.get("card"):
                outbound.append(
                    OutboundMessage(
                        channel=CHANNEL_RCS,
                        to=session.phone_number,
                        text=turn.reply_text,
                        card=turn.card,
                    )
                )
            elif esc.channel == CHANNEL_EMAIL:
                if current_channel == CHANNEL_EMAIL:
                    continue
                email_type = "agreement" if "loan_plan" in turn.data else "text"
                outbound.append(
                    OutboundMessage(
                        channel=CHANNEL_EMAIL,
                        to=session.phone_number,
                        text=turn.reply_text,
                        email_type=email_type,
                    )
                )
            elif esc.channel != current_channel:
                outbound.append(
                    OutboundMessage(
                        channel=esc.channel,
                        to=session.phone_number,
                        text=turn.reply_text,
                    )
                )
        return JourneyPlan(outbound=outbound, session=session, trace=trace)

    @staticmethod
    def _capture_kyc(session: Session, message: Message) -> None:
        body = (message.body or "").strip()
        kyc = session.state.setdefault("kyc", {})
        name = KYC_NAME_RE.search(body)
        state = KYC_STATE_RE.search(body)
        if name:
            kyc["name"] = name.group(1).strip()
        if state:
            kyc["state"] = state.group(1).strip()

    @staticmethod
    def _reserve(session: Session, message: Message) -> dict:
        match = RESERVE_RE.search(message.body or "")
        sku = match.group(1).upper() if match else session.state.get("product_sku", "NPK151515")
        return {"sku": sku, "reserved_at": message.ts}

    @staticmethod
    def _classify(session: Session) -> str:
        latest = session.conversation[-1]
        body = (latest.body or "").strip().upper()
        if latest.media_url:
            return "photo_diagnosis"
        reserve_intent = ("RESERVE" in body) or (
            session.state.get("quote") and any(w in body for w in ("YES", "CONFIRM", "OK"))
        )
        if reserve_intent:
            return "reserve"
        finance_intent = ("FINANCE", "LOAN", "CAN'T AFFORD", "CANT AFFORD", "INSTALLMENT", "BNPL")
        if any(w in body for w in finance_intent):
            return "finance"
        if any(w in body for w in ("PRICE", "BUY", "STOCK", "DEALER", "COST")):
            return "commerce"
        if any(w in body for w in ("HI", "HELLO", "WHO ARE YOU", "HELP")):
            return "chitchat"
        pest_words = ("YELLOW", "LEAF", "LEAVES", "MAIZE", "CROP", "DYING", "WILT", "DISEASE")
        if any(w in body for w in pest_words):
            return "photo_diagnosis"
        return "photo_diagnosis"
