from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ApiResponse
from app.dependencies.auth import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import LoginData, UserLogin
from app.schemas.user import UserPublic, UserRegister
from app.services.user import (
    InvalidCredentialsError,
    PhoneAlreadyRegisteredError,
    login_user,
    register_user,
)

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


@router.post(
    "/register",
    response_model=ApiResponse,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
)
async def register(
    user_data: UserRegister,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        user = await register_user(session, user_data)
    except PhoneAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该手机号已注册",
        ) from exc

    return ApiResponse.success(
        message="注册成功",
        data=UserPublic.model_validate(user),
    )


@router.post("/login", response_model=ApiResponse, summary="用户登录")
async def login(
    credentials: UserLogin,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        login_data = await login_user(session, credentials)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    return ApiResponse.success(message="登录成功", data=login_data)


@router.get(
    "/me",
    response_model=ApiResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ApiResponse,
            "description": (
                "token invalid（缺失、格式错误或签名失败）、"
                "token expired（已过期）或 no permission（Token 类型不匹配）"
            ),
        }
    },
    summary="获取当前用户",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> ApiResponse:
    return ApiResponse.success(
        message="请求成功",
        data=UserPublic.model_validate(current_user),
    )
