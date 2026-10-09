from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional


class ListDashboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int = Field(...)
    refresh_token: Optional[str] = Field(None)