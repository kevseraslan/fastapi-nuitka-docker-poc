from __future__ import annotations

from typing import Dict

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.refresh_tokens import RefreshTokens


async def invalidateRefreshToken(db: AsyncSession, refresh_token: str, user_id: int) -> Dict[str, int]:
    """
    Revokes (or deletes) a single refresh token belonging to a user.

    Security note:
    - We scope by both token and user_id to prevent token probing across users.
    - We revoke (soft-invalidate) instead of deleting to keep optional auditability.
    """
    stmt = (
        update(RefreshTokens)
        .where(
            RefreshTokens.token == refresh_token,
            RefreshTokens.user_id == user_id,
            RefreshTokens.is_revoked.is_(False),
        )
        .values(is_revoked=True)
    )

    result = await db.execute(stmt)
    await db.commit()

    # rowcount is the number of rows matched/updated
    deleted_count = int(result.rowcount or 0)
    return {"deleted_count": deleted_count}


async def invalidateAllUserTokens(db: AsyncSession, user_id: int) -> Dict[str, int]:
    """
    Revokes (or deletes) all active refresh tokens for a user.
    """
    stmt = (
        update(RefreshTokens)
        .where(
            RefreshTokens.user_id == user_id,
            RefreshTokens.is_revoked.is_(False),
        )
        .values(is_revoked=True)
    )

    result = await db.execute(stmt)
    await db.commit()

    deleted_count = int(result.rowcount or 0)
    return {"deleted_count": deleted_count}


async def logoutUser(db: AsyncSession, refresh_token: str, user_id: int) -> Dict[str, object]:
    """
    Main logout orchestration function.

    Behavior:
    1) Revoke the provided refresh token (best-effort).
    2) Optionally revoke all user's tokens if you want global sign-out behavior.
       Currently implemented as per given child definitions and order.

    Note:
    - Even if the specific token doesn't exist, we return success to avoid leaking token validity.
    """
    _ = await invalidateRefreshToken(db=db, refresh_token=refresh_token, user_id=user_id)
    _ = await invalidateAllUserTokens(db=db, user_id=user_id)

    return {"success": True, "message": "Logged out successfully."}