from fastapi import APIRouter, Depends
from schemas.register import RegisterBase, CreateRegisterResponse
from services.register_user_service import registerUser
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db

router = APIRouter(prefix="/register", tags=["register"])


@router.post("/", response_model=CreateRegisterResponse, status_code=201)
async def create_api_register_router(
    payload: RegisterBase,
    db: AsyncSession = Depends(get_db),
):
    result = await registerUser(email=payload.email, password=payload.password, db=db)
    await db.commit()
    return CreateRegisterResponse(
        user_id=result.get("user_id"),
        access_token=result.get("access_token"),
        refresh_token=result.get("refresh_token", result.get("refreshToken")),
    )