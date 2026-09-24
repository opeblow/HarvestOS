from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import require_dashboard_session
from app.notifications.service import get_notification_service

router = APIRouter(
    prefix="/api",
    tags=["notifications"],
    dependencies=[Depends(require_dashboard_session)],
)


@router.get("/notifications")
def list_notifications(
    limit: int = Query(default=50, ge=1, le=200),
    unread_only: bool = Query(default=False),
) -> dict:
    service = get_notification_service()
    items = service.list(limit=limit, unread_only=unread_only)
    return {
        "items": [notification.model_dump() for notification in items],
        "unread": service.unread_count(),
        "total": len(service.list(limit=1000)),
    }


@router.post("/notifications/read-all")
def mark_all_read() -> dict:
    service = get_notification_service()
    for notification in service.list(limit=1000, unread_only=True):
        service.mark_read(notification.id)
    return {"ok": True, "unread": service.unread_count()}


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: str) -> dict:
    service = get_notification_service()
    notification = service.mark_read(notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="notification not found")
    return {"ok": True, "unread": service.unread_count()}
