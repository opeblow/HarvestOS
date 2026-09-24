from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "storage": settings.storage, "agent_backend": settings.agent_backend}
