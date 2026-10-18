from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.config import config


def validate_password_byte_length(password: str) -> str:
    if len(password.encode("utf-8")) > config.PASSWORD_MAX_UTF8_BYTES:
        raise ValueError(
            f"密码 UTF-8 编码长度不能超过 {config.PASSWORD_MAX_UTF8_BYTES} 字节"
        )
    return password


Password = Annotated[
    str,
    Field(min_length=8, max_length=config.PASSWORD_MAX_UTF8_BYTES),
    AfterValidator(validate_password_byte_length),
]


class UserRegister(BaseModel):
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    password: Password


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str
    create_time: datetime
