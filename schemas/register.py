from pydantic import BaseModel, Field, ConfigDict, EmailStr


class RegisterBase(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password (plain text input)")


class CreateRegisterRequest(RegisterBase):
    pass


class CreateRegisterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int = Field(..., description="Created user id")
    access_token: str = Field(..., description="Access token")
    refresh_token: str = Field(..., description="Refresh token")