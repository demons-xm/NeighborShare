from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import Password


class AdminCredentials(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: Password


class AdminRegister(AdminCredentials):
    pass


class AdminLogin(AdminCredentials):
    pass


class AdminPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    create_time: datetime


class AdminLoginData(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    admin: AdminPublic
