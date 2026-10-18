from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ApiResponse
from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.cart import CartItemAdd, CartItemQuantityUpdate
from app.services.cart import (
    CartDishNotFoundError,
    CartDishUnavailableError,
    CartItemNotFoundError,
    add_cart_item,
    clear_cart,
    get_cart,
    remove_cart_item,
    update_cart_item_quantity,
)

router = APIRouter(prefix="/api/cart", tags=["购物车"])


@router.get("", summary="获取我的购物车")
async def read_cart(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    return ApiResponse.success(data=await get_cart(session, current_user.id))


@router.post(
    "/items",
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"model": ApiResponse, "description": "菜品不存在"},
        409: {"model": ApiResponse, "description": "菜品已下架"},
    },
    summary="添加菜品到购物车",
)
async def post_cart_item(
    item_data: CartItemAdd,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        cart = await add_cart_item(session, current_user.id, item_data)
    except CartDishNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="菜品不存在",
        ) from exc
    except CartDishUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="菜品已下架，不能加入购物车",
        ) from exc
    return ApiResponse.success(message="已加入购物车", data=cart)


@router.put(
    "/items/{dish_id}",
    responses={404: {"model": ApiResponse, "description": "购物车商品不存在"}},
    summary="修改购物车菜品数量",
)
async def put_cart_item(
    dish_id: int,
    item_data: CartItemQuantityUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        cart = await update_cart_item_quantity(
            session,
            current_user.id,
            dish_id,
            item_data.quantity,
        )
    except CartItemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="购物车商品不存在",
        ) from exc
    return ApiResponse.success(message="购物车数量已更新", data=cart)


@router.delete(
    "/items/{dish_id}",
    responses={404: {"model": ApiResponse, "description": "购物车商品不存在"}},
    summary="删除购物车菜品",
)
async def delete_cart_item(
    dish_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        cart = await remove_cart_item(session, current_user.id, dish_id)
    except CartItemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="购物车商品不存在",
        ) from exc
    return ApiResponse.success(message="购物车商品已删除", data=cart)


@router.delete("/items", summary="清空购物车")
async def delete_cart_items(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    cart = await clear_cart(session, current_user.id)
    return ApiResponse.success(message="购物车已清空", data=cart)
