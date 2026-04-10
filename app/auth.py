from __future__ import annotations

import os
from typing import Set

from fastapi import Header, HTTPException, status


def _strip_wrapping_quotes(value: str) -> str:
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1].strip()
    return v


def _load_allowed_keys_from_env() -> Set[str]:
    raw = os.getenv("API_KEYS", "").strip()
    if not raw:
        # Single-key setups often use API_KEY by mistake (e.g. Portainer UI).
        raw = os.getenv("API_KEY", "").strip()
    if not raw:
        return set()
    raw = _strip_wrapping_quotes(raw)
    # Support comma, semicolon, newline separated lists (avoid splitting on spaces — keys could contain spaces)
    for sep in (",", ";", "\n"):
        raw = raw.replace(sep, ",")
    keys: list[str] = []
    for k in raw.split(","):
        k = _strip_wrapping_quotes(k.strip())
        if k:
            keys.append(k)
    return set(keys)


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
    allowed = _load_allowed_keys_from_env()
    if not allowed:
        return
    token: str | None = None
    if x_api_key:
        token = _strip_wrapping_quotes(x_api_key.strip())
    if not token:
        token = _extract_bearer_token(authorization)
        if token:
            token = _strip_wrapping_quotes(token)
    if not token or token not in allowed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
