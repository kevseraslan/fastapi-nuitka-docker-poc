from pydantic import BaseModel, Field, ConfigDict, EmailStr


class LogoutBase(BaseModel):
    refresh_token: str = Field(..., min_length=1)
    user_id: int = Field(..., ge=1)


class CreateLogoutRequest(LogoutBase):
    pass


class CreateLogoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    success: bool
    message: str