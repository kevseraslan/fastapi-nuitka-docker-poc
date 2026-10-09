from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, Optional

import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.refresh_tokens import RefreshTokens
from models.users import Users

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthenticationError(ValueError):
    """Raised when credentials are invalid or user cannot authenticate."""


def verifyPassword(password: str, hashed_password: str) -> dict:
    is_valid = _pwd_context.verify(password, hashed_password)
    return {"is_valid": is_valid}


async def logLoginAttempt(email: str, success: bool, ip_address: str) -> dict:
    """
    Log login attempts.

    NOTE: No table defined in provided models_info for persistent logging.
    Implement integration with your logging/observability stack here.
    """
    # Production-grade logging without printing; works in API/CLI equally.
    # This does not require any ENV configuration and avoids placeholders.
    import logging

    logger = logging.getLogger("auth.login")
    logger.info(
        "login_attempt",
        extra={
            "email": email,
            "success": success,
            "ip_address": ip_address,
        },
    )
    # No persistent id available; return a stable sentinel id.
    return {"log_id": 0}


async def findUserByEmail(db: AsyncSession, email: str) -> dict:
    stmt = select(Users).where(Users.email == email)
    result = await db.execute(stmt)
    user: Optional[Users] = result.scalar_one_or_none()

    exists = user is not None
    user_id = int(user.id) if user else 0
    hashed_password = str(user.password_hash) if user else ""
    normalized_email = str(user.email) if user else email

    # Best-effort logging without coupling to DB; IP is not provided here.
    await logLoginAttempt(email=normalized_email, success=exists, ip_address="")

    return {
        "user_id": user_id,
        "email": normalized_email,
        "hashed_password": hashed_password,
        "exists": exists,
    }


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _generate_jwt(
    *,
    secret: str,
    algorithm: str,
    subject: str,
    claims: Dict[str, Any],
    expires_in_seconds: int,
) -> str:
    now = _utcnow()
    payload: Dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in_seconds)).timestamp()),
        **claims,
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def generateLoginTokens(user_id: int, email: str) -> dict:
    # (ZORUNLU) JWT token imzalama anahtarı (örn. uzun, rastgele bir secret).
    jwt_secret = _require_env("JWT_SECRET")

    # (OPSİYONEL) JWT algoritması (varsayılan: HS256).
    jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")

    # (OPSİYONEL) Access token süresi saniye cinsinden (varsayılan: 900).
    access_ttl_seconds_raw = os.getenv("ACCESS_TOKEN_TTL_SECONDS", "900")

    # (OPSİYONEL) Refresh token süresi saniye cinsinden (varsayılan: 2592000).
    refresh_ttl_seconds_raw = os.getenv("REFRESH_TOKEN_TTL_SECONDS", "2592000")

    try:
        access_ttl_seconds = int(access_ttl_seconds_raw)
        refresh_ttl_seconds = int(refresh_ttl_seconds_raw)
    except ValueError as exc:
        raise RuntimeError("Invalid token TTL env values; must be integers (seconds).") from exc

    if access_ttl_seconds <= 0 or refresh_ttl_seconds <= 0:
        raise RuntimeError("Token TTL values must be positive integers (seconds).")

    jwt_issuer = os.getenv("JWT_ISSUER", "auth-service")

    access_token = _generate_jwt(
        secret=jwt_secret,
        algorithm=jwt_algorithm,
        subject=str(user_id),
        claims={"email": email, "type": "access", "iss": jwt_issuer},
        expires_in_seconds=access_ttl_seconds,
    )

    refresh_token = _generate_jwt(
        secret=jwt_secret,
        algorithm=jwt_algorithm,
        subject=str(user_id),
        claims={"email": email, "type": "refresh", "iss": jwt_issuer},
        expires_in_seconds=refresh_ttl_seconds,
    )

    return {"access_token": access_token, "refresh_token": refresh_token}


async def storeLoginRefreshToken(
    db: AsyncSession, user_id: int, refresh_token: str, expires_at: datetime
) -> dict:
    if expires_at.tzinfo is not None:
        expires_at = expires_at.replace(tzinfo=None)
    token_row = RefreshTokens(
        user_id=user_id,
        token=refresh_token,
        expires_at=expires_at,
        is_revoked=False,
    )
    db.add(token_row)
    await db.flush()  # ensure token_row.id is populated
    return {"token_id": int(token_row.id)}


def _extract_exp_as_datetime(refresh_token: str, jwt_secret: str, jwt_algorithm: str) -> datetime:
    try:
        decoded = jwt.decode(
            refresh_token,
            jwt_secret,
            algorithms=[jwt_algorithm],
            options={"require": ["exp", "sub"], "verify_signature": True},
        )
    except jwt.PyJWTError as exc:
        raise RuntimeError("Generated refresh token could not be decoded/validated.") from exc

    exp = decoded.get("exp")
    if not isinstance(exp, (int, float)):
        raise RuntimeError("Refresh token payload missing valid 'exp' claim.")
    return datetime.fromtimestamp(int(exp), tz=UTC)


async def authenticateUser(db: AsyncSession, email: str, password: str) -> dict:
    user_result = await findUserByEmail(db=db, email=email)

    if not user_result["exists"]:
        await logLoginAttempt(email=email, success=False, ip_address="")
        raise AuthenticationError("Invalid email or password.")

    # Optional: enforce active users only if model supports it.
    stmt = select(Users).where(Users.id == user_result["user_id"])
    result = await db.execute(stmt)
    user: Optional[Users] = result.scalar_one_or_none()
    if not user:
        await logLoginAttempt(email=email, success=False, ip_address="")
        raise AuthenticationError("Invalid email or password.")

    if hasattr(user, "is_active") and not bool(user.is_active):
        await logLoginAttempt(email=email, success=False, ip_address="")
        raise AuthenticationError("User account is inactive.")

    verify_result = verifyPassword(password=password, hashed_password=user_result["hashed_password"])
    if not verify_result["is_valid"]:
        await logLoginAttempt(email=email, success=False, ip_address="")
        raise AuthenticationError("Invalid email or password.")

    tokens = generateLoginTokens(user_id=user_result["user_id"], email=user_result["email"])

    # (ZORUNLU) JWT token imzalama anahtarı (expires_at hesaplamak için gerekli).
    jwt_secret = _require_env("JWT_SECRET")
    # (OPSİYONEL) JWT algoritması (varsayılan: HS256).
    jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")

    refresh_expires_at = _extract_exp_as_datetime(
        tokens["refresh_token"],
        jwt_secret=jwt_secret,
        jwt_algorithm=jwt_algorithm,
    )

    await storeLoginRefreshToken(
        db=db,
        user_id=user_result["user_id"],
        refresh_token=tokens["refresh_token"],
        expires_at=refresh_expires_at,
    )

    await logLoginAttempt(email=email, success=True, ip_address="")

    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "user_id": user_result["user_id"],
    }