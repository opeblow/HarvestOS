from fastapi import APIRouter, Depends, Query

from app.agents.commerce import _load_dealers
from app.auth import require_dashboard_session
from app.notifications.service import get_notification_service
from app.services.journey import get_journey
from app.shared import Session

router = APIRouter(
    prefix="/api",
    tags=["dashboard"],
    dependencies=[Depends(require_dashboard_session)],
)


def _mask(phone: str) -> str:
    if len(phone) < 8:
        return phone
    return f"{phone[:3]}****{phone[-4:]}"


def _session_row(session: Session) -> dict:
    last = session.conversation[-1] if session.conversation else None
    diagnosis = session.state.get("diagnosis") or {}
    stages = {k: v for k, v in session.state.items() if isinstance(v, str) and k.endswith("stage")}
    return {
        "phone": _mask(session.phone_number),
        "channel": session.channel,
        "visited_channels": session.visited_channels,
        "last_message": (last.body if last else "")[:140],
        "last_ts": session.updated_ts,
        "diagnosis_issue": diagnosis.get("issue", ""),
        "order_status": session.state.get("order_status", ""),
        "has_loan": "loan_plan" in session.state,
        "stage": stages,
    }


@router.get("/stats")
def stats() -> dict:
    sessions = get_journey().store.list_sessions()
    channel_messages: dict[str, int] = {"sms": 0, "whatsapp": 0, "rcs": 0, "email": 0}
    for session in sessions:
        for message in session.conversation:
            channel_messages[message.channel] = channel_messages.get(message.channel, 0) + 1
    return {
        "sessions": len(sessions),
        "messages": sum(channel_messages.values()),
        "channel_messages": channel_messages,
        "diagnoses": sum(1 for s in sessions if s.state.get("diagnosis")),
        "quotes": sum(1 for s in sessions if s.state.get("quote")),
        "loans_issued": sum(1 for s in sessions if s.state.get("loan_plan")),
        "reservations": sum(1 for s in sessions if s.state.get("order_status")),
        "notifications": len(get_notification_service().list(limit=1000)),
    }


@router.get("/conversations")
def conversations(limit: int = Query(default=50, ge=1, le=200)) -> list[dict]:
    sessions = get_journey().store.list_sessions(limit=limit)
    return [_session_row(s) for s in sessions]


@router.get("/dealers")
def dealers() -> list[dict]:
    return _load_dealers()


@router.get("/loan-health")
def loan_health() -> dict:
    sessions = [s for s in get_journey().store.list_sessions() if s.state.get("loan_plan")]
    portfolio = sum(s.state["loan_plan"].get("amount_ngn", 0) for s in sessions)
    return {
        "active_loans": len(sessions),
        "portfolio_ngn": round(portfolio, 2),
    }
