from fastapi import APIRouter, Depends, Header, Query
from typing import Optional
from schemas.dashboard import ListDashboardResponse
from services.verify_access_token_service import verifyAccessToken
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.refresh_tokens import RefreshTokens
from database import get_db

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/", response_model=ListDashboardResponse, status_code=200)
async def get_api_dashboard_router(
    authorization: Optional[str] = Header(None),
    access_token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    token = ""
    if access_token:
        token = access_token
    elif authorization:
        token = authorization.split(" ")[1] if authorization.startswith("Bearer ") else authorization

    # verifyAccessToken is a synchronous function and does not take a db argument
    result = verifyAccessToken(access_token=token)
    user_id = result.get("user_id", 0)

    refresh_token = None
    if result.get("is_valid") and user_id > 0:
        stmt = select(RefreshTokens).where(
            RefreshTokens.user_id == user_id,
            RefreshTokens.is_revoked.is_(False)
        ).order_by(RefreshTokens.id.desc()).limit(1)
        db_res = await db.execute(stmt)
        token_row = db_res.scalar_one_or_none()
        if token_row:
            refresh_token = token_row.token

    return ListDashboardResponse(
        user_id=user_id,
        refresh_token=refresh_token
    )