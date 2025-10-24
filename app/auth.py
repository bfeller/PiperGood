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


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if not x_api_key or x_api_key not in ALLOWED_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
