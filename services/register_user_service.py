from __future__ import annotations

import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.refresh_tokens import RefreshTokens
from models.users import Users
from core.exceptions import ServiceError

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class ValidationError(ServiceError):
    def __init__(self, errors: list[dict[str, str]]):
        msg = errors[0]["message"] if errors and "message" in errors[0] else "Validation error"
        super().__init__(
            code="VALIDATION_ERROR",
            message=msg,
            details={"errors": errors},
            status_code=400,
        )
        self.errors = errors


class ConflictError(ServiceError):
    def __init__(self, message: str = "Resource conflict"):
        super().__init__(
            code="RESOURCE_EXISTS",
            message=message,
            status_code=409,
        )


class EmailSendError(Exception):
    pass


class EventPublishError(Exception):
    pass


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validateUserInput(email: str, password: str) -> dict:
    errors: list[dict[str, str]] = []

    normalized_email = (email or "").strip().lower()
    if not normalized_email:
        errors.append({"field": "email", "message": "Email is required."})
    elif len(normalized_email) > 254:
        errors.append({"field": "email", "message": "Email is too long."})
    elif not _EMAIL_RE.match(normalized_email):
        errors.append({"field": "email", "message": "Email format is invalid."})

    if password is None or password == "":
        errors.append({"field": "password", "message": "Password is required."})
    else:
        if len(password) < 8:
            errors.append({"field": "password", "message": "Password must be at least 8 characters long."})
        if len(password) > 1024:
            errors.append({"field": "password", "message": "Password is too long."})
        if not re.search(r"[A-Z]", password):
            errors.append({"field": "password", "message": "Password must contain at least one uppercase letter."})
        if not re.search(r"[0-9]", password):
            errors.append({"field": "password", "message": "Password must contain at least one digit."})
        if not re.search(r"[^a-zA-Z0-9]", password):
            errors.append({"field": "password", "message": "Password must contain at least one special character."})

    return {"is_valid": len(errors) == 0, "errors": errors}


async def checkEmailExists(db: AsyncSession, email: str) -> dict:
    normalized_email = (email or "").strip().lower()
    stmt = select(Users.id).where(Users.email == normalized_email).limit(1)
    result = await db.execute(stmt)
    exists = result.scalar_one_or_none() is not None
    return {"exists": exists}


def hashPassword(password: str) -> dict:
    hashed = _pwd_context.hash(password)
    return {"hashed_password": hashed}


async def createUserRecord(db: AsyncSession, email: str, hashed_password: str) -> dict:
    normalized_email = (email or "").strip().lower()

    user = Users(
        email=normalized_email,
        password_hash=hashed_password,
        is_active=True,
    )
    db.add(user)

    try:
        await db.flush()
    except Exception:
        # If a unique constraint exists on users.email, concurrent register attempts may fail here.
        raise

    created_at = datetime.now(timezone.utc)

    # Child orchestration for createUserRecord
# await sendWelcomeEmail(email=normalized_email, user_id=int(user.id))
    #await publishUserCreatedEvent(user_id=int(user.id), email=normalized_email)

    return {"user_id": int(user.id), "created_at": created_at}


def _getJwtSecret() -> str:
    # (ZORUNLU) JWT imzalama anahtarı (örn. uzun, rastgele bir string).
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET is required.")
    return secret


def _getJwtIssuer() -> str:
    # (OPSİYONEL) JWT issuer değeri (örn. 'my-service').
    return os.getenv("JWT_ISSUER", "auth-service")


def _getAccessTokenMinutes() -> int:
    # (OPSİYONEL) Access token geçerlilik süresi (dakika).
    raw = os.getenv("ACCESS_TOKEN_EXPIRES_MINUTES", "15")
    try:
        minutes = int(raw)
    except ValueError as e:
        raise RuntimeError("ACCESS_TOKEN_EXPIRES_MINUTES must be an integer.") from e
    if minutes <= 0 or minutes > 24 * 60:
        raise RuntimeError("ACCESS_TOKEN_EXPIRES_MINUTES out of allowed range.")
    return minutes


def _getRefreshTokenDays() -> int:
    # (OPSİYONEL) Refresh token geçerlilik süresi (gün).
    raw = os.getenv("REFRESH_TOKEN_EXPIRES_DAYS", "30")
    try:
        days = int(raw)
    except ValueError as e:
        raise RuntimeError("REFRESH_TOKEN_EXPIRES_DAYS must be an integer.") from e
    if days <= 0 or days > 365:
        raise RuntimeError("REFRESH_TOKEN_EXPIRES_DAYS out of allowed range.")
    return days


def generateAuthTokens(user_id: int, email: str) -> dict:
    secret = _getJwtSecret()
    issuer = _getJwtIssuer()
    now = datetime.now(timezone.utc)

    access_minutes = _getAccessTokenMinutes()
    access_exp = now + timedelta(minutes=access_minutes)

    # Access token (JWT)
    access_payload: dict[str, Any] = {
        "iss": issuer,
        "sub": str(user_id),
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int(access_exp.timestamp()),
        "type": "access",
        "jti": secrets.token_urlsafe(16),
    }
    access_token = jwt.encode(access_payload, secret, algorithm="HS256")

    # Refresh token: high-entropy opaque token (recommended to store hashed in DB in real systems)
    refresh_token = secrets.token_urlsafe(64)

    return {"access_token": access_token, "refresh_token": refresh_token}


async def saveRefreshToken(db: AsyncSession, user_id: int, refresh_token: str, expires_at: datetime) -> dict:
    if expires_at.tzinfo is not None:
        expires_at = expires_at.replace(tzinfo=None)
    token_row = RefreshTokens(
        user_id=user_id,
        token=refresh_token,
        expires_at=expires_at,
        is_revoked=False,
    )
    db.add(token_row)
    await db.flush()
    return {"token_id": int(token_row.id)}


async def sendWelcomeEmail(email: str, user_id: int) -> dict:
    # (ZORUNLU) SMTP sunucu adresi (örn. smtp.gmail.com).
    smtp_host = os.getenv("SMTP_HOST")
    # (OPSİYONEL) SMTP port (örn. 587).
    smtp_port_raw = os.getenv("SMTP_PORT", "587")
    # (ZORUNLU) SMTP kullanıcı adı.
    smtp_username = os.getenv("SMTP_USERNAME")
    # (ZORUNLU) SMTP şifresi.
    smtp_password = os.getenv("SMTP_PASSWORD")
    # (ZORUNLU) Gönderen e-posta adresi.
    smtp_from = os.getenv("SMTP_FROM")
    # (OPSİYONEL) SMTP TLS kullanımı ('true'/'false').
    smtp_use_tls_raw = os.getenv("SMTP_USE_TLS", "true")

    if not smtp_host or not smtp_username or not smtp_password or not smtp_from:
        raise EmailSendError("SMTP configuration is incomplete (SMTP_HOST/SMTP_USERNAME/SMTP_PASSWORD/SMTP_FROM).")

    try:
        smtp_port = int(smtp_port_raw)
    except ValueError as e:
        raise EmailSendError("SMTP_PORT must be an integer.") from e

    smtp_use_tls = smtp_use_tls_raw.strip().lower() in {"1", "true", "yes", "y", "on"}

    subject = "Welcome!"
    body = (
        f"Hello,\n\n"
        f"Welcome to our service. Your user id is {user_id}.\n\n"
        f"Best regards,\n"
        f"Our Team\n"
    )

    import asyncio
    import smtplib
    from email.message import EmailMessage

    msg = EmailMessage()
    msg["From"] = smtp_from
    msg["To"] = email
    msg["Subject"] = subject
    msg.set_content(body)

    def _send() -> None:
        with smtplib.SMTP(host=smtp_host, port=smtp_port, timeout=15) as server:
            server.ehlo()
            if smtp_use_tls:
                server.starttls()
                server.ehlo()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)

    try:
        await asyncio.to_thread(_send)
    except Exception as e:
        raise EmailSendError("Failed to send welcome email.") from e

    # SMTP does not provide a message id reliably; generate a local one for traceability.
    message_id = secrets.token_urlsafe(16)
    return {"queued": True, "message_id": message_id}


async def publishUserCreatedEvent(user_id: int, email: str) -> dict:
    # (ZORUNLU) Event publish için HTTP endpoint (örn. https://events.example.com/publish).
    event_publish_url = os.getenv("EVENT_PUBLISH_URL")
    # (OPSİYONEL) Event publish API anahtarı.
    event_publish_api_key = os.getenv("EVENT_PUBLISH_API_KEY")

    if not event_publish_url:
        raise EventPublishError("EVENT_PUBLISH_URL is required.")

    import httpx

    payload = {
        "event": "user.created",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "data": {"user_id": user_id, "email": email},
    }

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if event_publish_api_key:
        headers["Authorization"] = f"Bearer {event_publish_api_key}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(event_publish_url, json=payload, headers=headers)
            resp.raise_for_status()
    except Exception as e:
        raise EventPublishError("Failed to publish user.created event.") from e

    return {"success": True}


async def registerUser(db: AsyncSession, email: str, password: str) -> dict:
    validation = validateUserInput(email=email, password=password)
    if not validation["is_valid"]:
        raise ValidationError(validation["errors"])

    exists_result = await checkEmailExists(db=db, email=email)
    if exists_result["exists"]:
        raise ConflictError("Email already exists.")

    hashed_result = hashPassword(password=password)

    user_record = await createUserRecord(
        db=db,
        email=email,
        hashed_password=hashed_result["hashed_password"],
    )

    tokens = generateAuthTokens(user_id=user_record["user_id"], email=(email or "").strip().lower())

    refresh_days = _getRefreshTokenDays()
    expires_at = datetime.now(timezone.utc) + timedelta(days=refresh_days)
    await saveRefreshToken(
        db=db,
        user_id=user_record["user_id"],
        refresh_token=tokens["refresh_token"],
        expires_at=expires_at,
    )

    # Commit should be controlled by the caller's unit-of-work boundaries.
    return {
        "user_id": user_record["user_id"],
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
    }