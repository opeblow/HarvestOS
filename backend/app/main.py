from __future__ import annotations

import os

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from app.config import settings
from app.routers import dashboard, webhooks
from app.routers import router as health_router

SENSITIVE_KEYS = {"text", "mediaurl", "phonenumber", "body", "message", "from", "recipient"}


def _before_send(event: dict, hint: dict) -> dict | None:
    def scrub(obj) -> object:
        if isinstance(obj, dict):
            return {
                k: ("[redacted]" if k.lower() in SENSITIVE_KEYS else scrub(v))
                for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [scrub(v) for v in obj]
        return obj

    return scrub(event)  # type: ignore[return-value]


def _init_sentry() -> None:
    dsn = settings.sentry_dsn or os.getenv("SENTRY_DSN", "")
    if not dsn:
        return
    sentry_sdk.init(
        dsn=dsn,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            StarletteIntegration(transaction_style="endpoint"),
        ],
        before_send=_before_send,
        send_default_pii=False,
        environment=settings.app_env,
    )


_init_sentry()

app = FastAPI(title="HarvestOS API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET"],
    allow_headers=["Accept"],
)

app.include_router(health_router)
app.include_router(webhooks.router)
app.include_router(dashboard.router)
