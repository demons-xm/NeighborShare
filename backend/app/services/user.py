from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.models.user import User
from app.schemas.auth import LoginData, UserLogin
from app.schemas.user import UserRegister
from app.utils.password import hash_password, verify_password
from app.utils.token import create_access_token


class PhoneAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


async def register_user(session: AsyncSession, user_data: UserRegister) -> User:
    existing_user = await session.scalar(
        select(User.id).where(User.phone == user_data.phone)
    )
    if existing_user is not None:
        raise PhoneAlreadyRegisteredError

    user = User(
        phone=user_data.phone,
        password_hash=hash_password(user_data.password),
    )
    session.add(user)

    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise PhoneAlreadyRegisteredError from exc

    return user


async def login_user(session: AsyncSession, credentials: UserLogin) -> LoginData:
    user = await session.scalar(select(User).where(User.phone == credentials.phone))
    if (
        user is None
        or not user.is_active
        or not verify_password(credentials.password, user.password_hash)
    ):
        raise InvalidCredentialsError("手机号或密码错误")

    return LoginData(
        access_token=create_access_token(subject=str(user.id)),
        expires_in=config.ACCESS_TOKEN_EXPIRE_HOURS * 60 * 60,
        user=user,
    )
