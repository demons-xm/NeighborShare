from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ApiResponse
from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.address import AddressCreate, AddressPublic, AddressUpdate
from app.services.address import (
    AddressNotFoundError,
    create_address,
    delete_address,
    list_addresses,
    set_default_address,
    update_address,
)

router = APIRouter(prefix="/api/address", tags=["收货地址"])


@router.get("", response_model=ApiResponse, summary="获取我的收货地址")
async def get_addresses(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    addresses = await list_addresses(session, current_user.id)
    return ApiResponse.success(
        data=[AddressPublic.model_validate(address) for address in addresses]
    )


@router.post(
    "",
    response_model=ApiResponse,
    status_code=status.HTTP_201_CREATED,
    summary="新增收货地址",
)
async def post_address(
    address_data: AddressCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    address = await create_address(session, current_user.id, address_data)
    return ApiResponse.success(
        message="收货地址添加成功",
        data=AddressPublic.model_validate(address),
    )


@router.put(
    "/{address_id}",
    response_model=ApiResponse,
    responses={404: {"model": ApiResponse, "description": "收货地址不存在"}},
    summary="编辑收货地址",
)
async def put_address(
    address_id: int,
    address_data: AddressUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        address = await update_address(
            session,
            current_user.id,
            address_id,
            address_data,
        )
    except AddressNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="收货地址不存在",
        ) from exc
    return ApiResponse.success(
        message="收货地址更新成功",
        data=AddressPublic.model_validate(address),
    )


@router.delete(
    "/{address_id}",
    response_model=ApiResponse,
    responses={404: {"model": ApiResponse, "description": "收货地址不存在"}},
    summary="删除收货地址",
)
async def remove_address(
    address_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        await delete_address(session, current_user.id, address_id)
    except AddressNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="收货地址不存在",
        ) from exc
    return ApiResponse.success(message="收货地址删除成功")


@router.put(
    "/{address_id}/default",
    response_model=ApiResponse,
    responses={404: {"model": ApiResponse, "description": "收货地址不存在"}},
    summary="设为默认收货地址",
)
async def put_default_address(
    address_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        address = await set_default_address(session, current_user.id, address_id)
    except AddressNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="收货地址不存在",
        ) from exc
    return ApiResponse.success(
        message="默认收货地址设置成功",
        data=AddressPublic.model_validate(address),
    )
