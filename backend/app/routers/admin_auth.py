from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ApiResponse
from app.db.database import get_db
from app.schemas.admin import AdminLogin, AdminPublic, AdminRegister
from app.services.admin import (
    AdminUsernameAlreadyRegisteredError,
    InvalidAdminCredentialsError,
    login_admin,
    register_admin,
)

router = APIRouter(prefix="/api/admin/auth", tags=["商家管理员认证"])


@router.post(
    "/register",
    response_model=ApiResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_409_CONFLICT: {
            "model": ApiResponse,
            "description": "管理员用户名已注册",
        }
    },
    summary="商家注册",
)
async def admin_register(
    credentials: AdminRegister,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        admin = await register_admin(session, credentials)
    except AdminUsernameAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="管理员用户名已注册",
        ) from exc

    return ApiResponse.success(
        message="商家注册成功，请登录",
        data=AdminPublic.model_validate(admin),
    )


@router.post(
    "/login",
    response_model=ApiResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ApiResponse,
            "description": "管理员账号或密码错误",
        }
    },
    summary="商家管理员登录",
)
async def admin_login(
    credentials: AdminLogin,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        login_data = await login_admin(session, credentials)
    except InvalidAdminCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="管理员账号或密码错误",
        ) from exc

    return ApiResponse.success(message="管理员登录成功", data=login_data)
