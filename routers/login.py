from fastapi import APIRouter, Depends
from schemas.login import LoginBase, CreateLoginResponse
from services.authenticate_user_service import authenticateUser
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db

router = APIRouter(prefix="/login", tags=["login"])


@router.post("/", response_model=CreateLoginResponse, status_code=201)
async def create_api_login_router(
    payload: LoginBase,
    db: AsyncSession = Depends(get_db),
):
    result = await authenticateUser(
        email=payload.email,
        password=payload.password,
        db=db,
    )
    await db.commit()

    return CreateLoginResponse(
        access_token=result.get("access_token") or result.get("accessToken"),
        refresh_token=result.get("refresh_token") or result.get("refreshToken"),
        user_id=result.get("user_id") or result.get("userId"),
    )