from datetime import datetime, timedelta, timezone
from typing import Literal

import jwt

from app.config import config

TokenType = Literal["user", "admin"]


def create_access_token(
    subject: str,
    token_type: TokenType = "user",
    expires_delta: timedelta | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(hours=config.ACCESS_TOKEN_EXPIRE_HOURS)
    )
    payload = {
        "sub": subject,
        "type": token_type,
        "exp": expires_at,
    }
    return jwt.encode(
        payload,
        config.JWT_SECRET_KEY,
        algorithm=config.JWT_ALGORITHM,
    )
