from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.models.admin import Admin
from app.schemas.admin import AdminLogin, AdminLoginData, AdminRegister
from app.utils.password import hash_password, verify_password
from app.utils.token import create_access_token


class InvalidAdminCredentialsError(Exception):
    pass


class AdminUsernameAlreadyRegisteredError(Exception):
    pass


async def register_admin(
    session: AsyncSession,
    credentials: AdminRegister,
) -> Admin:
    existing_admin = await session.scalar(
        select(Admin.id).where(Admin.username == credentials.username)
    )
    if existing_admin is not None:
        raise AdminUsernameAlreadyRegisteredError

    admin = Admin(
        username=credentials.username,
        password_hash=hash_password(credentials.password),
    )
    try:
        async with session.begin_nested():
            session.add(admin)
            await session.flush()
    except IntegrityError as exc:
        existing_admin = await session.scalar(
            select(Admin.id).where(Admin.username == credentials.username)
        )
        if existing_admin is not None:
            raise AdminUsernameAlreadyRegisteredError from exc
        raise
    return admin


async def login_admin(
    session: AsyncSession,
    credentials: AdminLogin,
) -> AdminLoginData:
    admin = await session.scalar(
        select(Admin).where(Admin.username == credentials.username)
    )
    if (
        admin is None
        or not admin.is_active
        or not verify_password(credentials.password, admin.password_hash)
    ):
        raise InvalidAdminCredentialsError

    return AdminLoginData(
        access_token=create_access_token(
            subject=str(admin.id),
            token_type="admin",
        ),
        expires_in=config.ACCESS_TOKEN_EXPIRE_HOURS * 60 * 60,
        admin=admin,
    )


async def ensure_bootstrap_admin(
    session: AsyncSession,
    username: str | None,
    password: str | None,
) -> None:
    if username is None and password is None:
        return
    if username is None or password is None:
        raise RuntimeError(
            "ADMIN_USERNAME and ADMIN_PASSWORD must be configured together"
        )
    if not 3 <= len(username) <= 50:
        raise RuntimeError("ADMIN_USERNAME must contain 3 to 50 characters")
    if (
        not 8 <= len(password)
        or len(password.encode("utf-8")) > config.PASSWORD_MAX_UTF8_BYTES
    ):
        raise RuntimeError(
            "ADMIN_PASSWORD must contain at least 8 characters "
            "and no more than "
            f"{config.PASSWORD_MAX_UTF8_BYTES} UTF-8 bytes"
        )

    existing_admin = await session.scalar(
        select(Admin.id).where(Admin.username == username)
    )
    if existing_admin is not None:
        return

    try:
        async with session.begin_nested():
            session.add(
                Admin(
                    username=username,
                    password_hash=hash_password(password),
                )
            )
            await session.flush()
    except IntegrityError:
        existing_admin = await session.scalar(
            select(Admin.id).where(Admin.username == username)
        )
        if existing_admin is None:
            raise
