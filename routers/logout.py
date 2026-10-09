from fastapi import APIRouter, Depends
from schemas.logout import LogoutBase, CreateLogoutResponse
from services.logout_user_service import logoutUser
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db

router = APIRouter(prefix="/logout", tags=["logout"])


@router.post("/", response_model=CreateLogoutResponse, status_code=201)
async def create_api_logout_router(
    payload: LogoutBase,
    Authorization: str | None = None,
    refresh_token: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    service_result = await logoutUser(
        refresh_token=payload.refresh_token,
        user_id=payload.user_id,
        db=db,
    )

    is_success = (
        service_result.get("success")
        if service_result.get("success") is not None
        else service_result.get("isSuccessful", False)
    )

    return CreateLogoutResponse(
        success=bool(is_success),
        message=service_result.get("message")
        if is_success
        else (service_result.get("errorMessage") or service_result.get("error")),
    )