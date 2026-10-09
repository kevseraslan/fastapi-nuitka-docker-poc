from pydantic import BaseModel, Field, ConfigDict, EmailStr


class LoginBase(BaseModel):
    email: EmailStr = Field(...)
    password: str = Field(..., min_length=1)


class CreateLoginRequest(LoginBase):
    pass


class CreateLoginResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str = Field(...)
    refresh_token: str = Field(...)
    user_id: int = Field(...)