from __future__ import annotations

import os
from typing import Set

from fastapi import Header, HTTPException, status


def _load_allowed_keys_from_env() -> Set[str]:
    raw = os.getenv("API_KEYS", "").strip()
    if not raw:
        return set()
    # Support comma, semicolon, whitespace separated lists
    separators = [",", ";", "\n", " "]
    for sep in separators:
        raw = raw.replace(sep, ",")
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    return set(keys)


ALLOWED_KEYS = _load_allowed_keys_from_env()


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


def require_api_key(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
) -> None:
    """Accept API key via ``x-api-key`` or ``Authorization: Bearer`` (OpenAI-style)."""
    if not ALLOWED_KEYS:
        return
    token: str | None = None
    if x_api_key:
        token = x_api_key.strip()
    if not token:
        token = _extract_bearer_token(authorization)
    if not token or token not in ALLOWED_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
