from __future__ import annotations

from app.agents.orchestrator import Orchestrator
from app.config import settings
from app.notifications.service import NotificationService, get_notification_service
from app.shared import Message, SendReceipt
from app.shared.session_store import SessionStore, SessionStoreFactory

_service: JourneyService | None = None


def get_journey() -> JourneyService:
    global _service
    if _service is None:
        _service = JourneyService(SessionStoreFactory.create(settings))
    return _service


class JourneyService:
    """Drives one inbound message through the orchestrator and delivers replies.

    Delivery always records an in-app notification; external channel delivery is
    attempted only through optional providers that are explicitly enabled.
    """

    def __init__(
        self,
        store: SessionStore | None = None,
        notifications: NotificationService | None = None,
    ) -> None:
        self.store = store or SessionStoreFactory.create(settings)
        self.orchestrator = Orchestrator()
        self.notifications = notifications or get_notification_service()

    def handle_inbound(self, message: Message) -> list[SendReceipt]:
        session = self.store.append_message(message.from_number, message)
        plan = self.orchestrator.handle(session, message)
        self.store.put(plan.session)
        receipts = [self.notifications.deliver(msg) for msg in plan.outbound]
        if settings.app_env == "dev":
            trace = " -> ".join(f"{t.agent}({t.intent})" for t in plan.trace)
            print(f"[harvestos] {message.from_number} [{message.channel}] trace: {trace}")
        return receipts
