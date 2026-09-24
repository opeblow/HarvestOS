from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from fastapi import Header, HTTPException

from app.config import settings


def _decode_segment(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def verify_dashboard_token(token: str) -> dict | None:
    secret = settings.dashboard_session_secret
    if len(secret) < 32:
        return None
    try:
        payload, signature = token.split(".", 1)
        expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _decode_segment(signature)):
            return None
        claims = json.loads(_decode_segment(payload))
        if not isinstance(claims, dict):
            return None
        now = int(time.time())
        if (
            claims.get("iss") != "harvestos"
            or claims.get("aud") != "partner-dashboard"
            or not claims.get("sub")
            or int(claims.get("exp", 0)) <= now
            or int(claims.get("iat", now + 1)) > now + 60
        ):
            return None
        return claims
    except (ValueError, TypeError, OverflowError, json.JSONDecodeError):
        return None


async def require_dashboard_session(
    authorization: str | None = Header(default=None),
) -> str:
    # Local development keeps direct API access convenient; deployed environments fail closed.
    if settings.app_env.lower() in {"dev", "development", "test"}:
        return "local-development"

    if len(settings.dashboard_session_secret) < 32:
        raise HTTPException(status_code=503, detail="dashboard authentication is not configured")
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not verify_dashboard_token(token):
        raise HTTPException(status_code=401, detail="authentication required")
    return "partner-dashboard"
