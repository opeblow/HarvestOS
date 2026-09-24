from __future__ import annotations

from app.agents.orchestrator import Orchestrator
from app.channels.base import ChannelAdapter
from app.channels.email import build_receipt_pdf
from app.channels.factory import registry
from app.config import settings
from app.shared import Message, SendReceipt
from app.shared.session_store import SessionStore, SessionStoreFactory

_service: JourneyService | None = None


def get_journey() -> JourneyService:
    global _service
    if _service is None:
        _service = JourneyService(SessionStoreFactory.create(settings))
    return _service


class JourneyService:
    def __init__(self, store: SessionStore | None = None) -> None:
        self.store = store or SessionStoreFactory.create(settings)
        self.orchestrator = Orchestrator()
        self.adapters: set[ChannelAdapter] = {registry.sms, registry.whatsapp, registry.email}

    def handle_inbound(self, message: Message) -> list[SendReceipt]:
        session = self.store.append_message(message.from_number, message)
        plan = self.orchestrator.handle(session, message)
        self.store.put(plan.session)
        receipts = [self._deliver(msg) for msg in plan.outbound]
        if settings.app_env == "dev":
            trace = " -> ".join(f"{t.agent}({t.intent})" for t in plan.trace)
            print(f"[harvestos] {message.from_number} [{message.channel}] trace: {trace}")
        return receipts

    def _deliver(self, message) -> SendReceipt:
        if message.channel == "email":
            self._attach_agreement(message)
        adapter = registry.dispatch(message.channel)
        return adapter.send(message)

    @staticmethod
    def _attach_agreement(message) -> None:
        if message.email_type == "agreement" and not message.attachments:
            reference = "HS-LOAN-DEMO"
            pdf = build_receipt_pdf(
                reference=reference,
                product="NPK 15-15-15 (50kg)",
                amount_ngn=18500.0,
                recipient=message.to,
            )
            message.attachments.append({"name": f"{reference}.pdf", "content": pdf})
