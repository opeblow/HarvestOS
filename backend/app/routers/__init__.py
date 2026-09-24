from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict:
    return {
        "ok": True,
        "storage": settings.storage,
        "agent_backend": settings.agent_backend,
        "asset_storage": settings.asset_storage,
        "notifications": {
            "provider": settings.notification_provider,
            "email": settings.email_provider,
            "sms": settings.sms_provider,
            "whatsapp": settings.whatsapp_provider,
        },
    }
