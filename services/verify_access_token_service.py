from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import jwt
from jwt import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.users import Users


class AccessTokenError(Exception):
    """Raised when access token validation fails."""


def _getJwtConfig() -> Tuple[str, str, str]:
    # (ZORUNLU) JWT imzalama anahtarı (secret) - access token doğrulaması için gereklidir.
    jwt_secret = os.getenv("JWT_SECRET")
    if not jwt_secret:
        raise RuntimeError("JWT_SECRET is required to verify access tokens.")

    # (OPSİYONEL) JWT algoritması (varsayılan: HS256).
    jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")

    # (ZORUNLU) Access token issuer değeri (token'ların bu servis tarafından üretildiğini doğrulamak için).
    jwt_issuer = os.getenv("JWT_ISSUER", "auth-service")

    return jwt_secret, jwt_algorithm, jwt_issuer


def verifyAccessToken(access_token: str) -> dict:
    """
    Validates the dashboard access token and extracts user_id.

    Expected JWT claims:
      - sub: user id (int or numeric string)
      - exp: expiration (unix timestamp)
      - iss: issuer
      - typ: optional; if present should be "access"
    """
    if not access_token or not isinstance(access_token, str):
        return {"is_valid": False, "user_id": 0}

    jwt_secret, jwt_algorithm, jwt_issuer = _getJwtConfig()

    try:
        payload = jwt.decode(
            access_token,
            jwt_secret,
            algorithms=[jwt_algorithm],
            issuer=jwt_issuer,
            options={
                "require": ["exp", "sub", "iss"],
                "verify_signature": True,
                "verify_exp": True,
                "verify_iss": True,
            },
        )
    except InvalidTokenError as e:
        import logging
        logger = logging.getLogger("auth.verify")
        logger.warning(f"JWT Verification failed: {e}")
        return {"is_valid": False, "user_id": 0}

    token_type = payload.get("typ")
    if token_type is not None and token_type != "access":
        return {"is_valid": False, "user_id": 0}

    sub = payload.get("sub")
    try:
        user_id = int(sub)
        if user_id <= 0:
            return {"is_valid": False, "user_id": 0}
    except (TypeError, ValueError):
        return {"is_valid": False, "user_id": 0}

    return {"is_valid": True, "user_id": user_id}


async def getUserProfileData(db: AsyncSession, user_id: int) -> dict:
    """
    Loads user-specific data after token validation.

    Returns:
      - user_data: basic user information
      - dashboard_data: user-specific dashboard payload (can be extended)
    """
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("user_id must be a positive integer.")

    stmt = select(Users).where(Users.id == user_id)
    result = await db.execute(stmt)
    user: Optional[Users] = result.scalar_one_or_none()

    if user is None:
        raise AccessTokenError("User not found.")
    if hasattr(user, "is_active") and not bool(user.is_active):
        raise AccessTokenError("User is inactive.")

    user_data: Dict[str, Any] = {
        "id": int(user.id),
        "email": str(user.email),
        "is_active": bool(getattr(user, "is_active", True)),
    }

    # Minimal, practical dashboard payload. Extend as needed.
    dashboard_data: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": [],
        "summary": {},
    }

    return {"user_data": user_data, "dashboard_data": dashboard_data}


def filterDashboardData(user_id: int, query_params: object) -> dict:
    """
    Filters dashboard data based on query parameters.

    This function is intentionally generic and does not assume a specific dashboard schema.
    It returns a normalized filter object that can be used by callers to filter/shape data.
    """
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("user_id must be a positive integer.")

    if query_params is None:
        query: Dict[str, Any] = {}
    elif isinstance(query_params, dict):
        query = query_params
    else:
        # If caller passes a pydantic model or any object with dict-like export.
        to_dict = getattr(query_params, "dict", None)
        if callable(to_dict):
            query = to_dict()
        else:
            query = dict(getattr(query_params, "__dict__", {}) or {})

    # Allowlist common filtering controls; everything else is preserved under "raw".
    allowed_keys = {"q", "from", "to", "limit", "offset", "sort", "order", "status", "type"}
    normalized: Dict[str, Any] = {}

    for k, v in query.items():
        if k in allowed_keys:
            normalized[k] = v

    # Basic normalization for pagination fields
    if "limit" in normalized:
        try:
            normalized["limit"] = max(1, min(500, int(normalized["limit"])))
        except (TypeError, ValueError):
            normalized.pop("limit", None)

    if "offset" in normalized:
        try:
            normalized["offset"] = max(0, int(normalized["offset"]))
        except (TypeError, ValueError):
            normalized.pop("offset", None)

    # Attach remaining parameters for advanced usage without breaking compatibility
    raw = {k: v for k, v in query.items() if k not in normalized}
    if raw:
        normalized["raw"] = raw

    normalized["user_id"] = user_id
    return {"filtered_data": normalized}