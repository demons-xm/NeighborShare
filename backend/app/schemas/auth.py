from pydantic import BaseModel, Field

from app.schemas.user import Password, UserPublic


class UserLogin(BaseModel):
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    password: Password


class LoginData(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: UserPublic
