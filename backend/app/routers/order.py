from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ApiResponse
from app.config import config
from app.db.database import get_db
from app.dependencies.auth import get_current_admin, get_current_user
from app.models.user import User
from app.schemas.order import OrderCreate, OrderPublic, OrderStatusUpdate
from app.services.order import (
    EmptyCartError,
    MinimumOrderAmountError,
    OrderAddressNotFoundError,
    OrderNotFoundError,
    OrderStatusConflictError,
    ShopClosedError,
    cancel_user_order,
    confirm_user_receipt,
    create_order,
    get_user_order,
    list_admin_orders,
    list_user_orders,
    simulate_user_payment,
    update_order_status,
)

router = APIRouter(tags=["订单"])
Page = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=config.MAX_PAGE_SIZE)]


@router.post(
    "/api/orders",
    response_model=ApiResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ApiResponse, "description": "用户 JWT 无效"},
        404: {"model": ApiResponse, "description": "收货地址不属于当前用户"},
        409: {"model": ApiResponse, "description": "店铺打烊、起送金额不足或菜品不可下单"},
    },
    summary="提交订单",
)
async def post_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        order = await create_order(session, current_user.id, order_data)
    except OrderAddressNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="收货地址不存在",
        ) from exc
    except EmptyCartError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="购物车为空",
        ) from exc
    except ShopClosedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="店铺当前未营业，暂不可下单",
        ) from exc
    except MinimumOrderAmountError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="菜品金额未达到起送价",
        ) from exc
    except OrderStatusConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return ApiResponse.success(
        message="订单创建成功",
        data=OrderPublic.model_validate(order),
    )


@router.get("/api/orders", response_model=ApiResponse, summary="查询我的订单")
async def get_orders(
    page: Page = 1,
    page_size: PageSize = config.DEFAULT_PAGE_SIZE,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    orders = await list_user_orders(
        session,
        current_user.id,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return ApiResponse.success(
        data=[OrderPublic.model_validate(order) for order in orders]
    )


@router.get(
    "/api/orders/{order_id}",
    response_model=ApiResponse,
    responses={404: {"model": ApiResponse, "description": "订单不存在"}},
    summary="查询我的订单详情",
)
async def get_order_detail(
    order_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        order = await get_user_order(session, current_user.id, order_id)
    except OrderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在",
        ) from exc
    return ApiResponse.success(data=OrderPublic.model_validate(order))


@router.post(
    "/api/orders/{order_id}/cancel",
    response_model=ApiResponse,
    responses={
        404: {"model": ApiResponse, "description": "订单不存在"},
        409: {"model": ApiResponse, "description": "只有待付款订单可以取消"},
    },
    summary="取消未付款订单",
)
async def post_cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        order = await cancel_user_order(session, current_user.id, order_id)
    except OrderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在",
        ) from exc
    except OrderStatusConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return ApiResponse.success(
        message="订单已取消",
        data=OrderPublic.model_validate(order),
    )


@router.post(
    "/api/orders/{order_id}/pay",
    response_model=ApiResponse,
    responses={
        404: {"model": ApiResponse, "description": "订单不存在"},
        409: {"model": ApiResponse, "description": "订单状态不允许支付"},
        503: {"model": ApiResponse, "description": "模拟支付未启用"},
    },
    summary="开发环境模拟支付",
)
async def post_simulated_payment(
    order_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    if (
        config.APP_ENV != "development"
        or not config.ENABLE_SIMULATED_PAYMENTS
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="模拟支付仅在开发环境显式启用后可用",
        )
    try:
        order = await simulate_user_payment(session, current_user.id, order_id)
    except OrderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在",
        ) from exc
    except OrderStatusConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return ApiResponse.success(
        message="开发环境模拟支付成功",
        data=OrderPublic.model_validate(order),
    )


@router.post(
    "/api/orders/{order_id}/confirm-receipt",
    response_model=ApiResponse,
    responses={
        404: {"model": ApiResponse, "description": "订单不存在"},
        409: {"model": ApiResponse, "description": "订单状态不允许确认收货"},
    },
    summary="确认收货",
)
async def post_confirm_receipt(
    order_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        order = await confirm_user_receipt(session, current_user.id, order_id)
    except OrderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在",
        ) from exc
    except OrderStatusConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return ApiResponse.success(
        message="已确认收货",
        data=OrderPublic.model_validate(order),
    )


@router.get(
    "/api/admin/orders",
    response_model=ApiResponse,
    responses={401: {"model": ApiResponse, "description": "管理员 JWT 无效或无权限"}},
    summary="管理员查询全部订单",
)
async def get_admin_orders(
    page: Page = 1,
    page_size: PageSize = config.DEFAULT_PAGE_SIZE,
    order_status: str | None = Query(
        default=None,
        alias="status",
        pattern="^(pending_payment|pending_acceptance|pending_delivery|completed|cancelled)$",
    ),
    _admin_id: str = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    orders = await list_admin_orders(
        session,
        status_filter=order_status,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return ApiResponse.success(
        data=[OrderPublic.model_validate(order) for order in orders]
    )


@router.patch(
    "/api/admin/orders/{order_id}/status",
    response_model=ApiResponse,
    responses={
        401: {"model": ApiResponse, "description": "管理员 JWT 无效或无权限"},
        404: {"model": ApiResponse, "description": "订单不存在"},
        409: {"model": ApiResponse, "description": "不允许的订单状态流转"},
    },
    summary="管理员更新订单状态",
)
async def patch_admin_order_status(
    order_id: int,
    update_data: OrderStatusUpdate,
    _admin_id: str = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        order = await update_order_status(
            session,
            order_id,
            update_data.status,
        )
    except OrderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在",
        ) from exc
    except OrderStatusConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return ApiResponse.success(
        message="订单状态更新成功",
        data=OrderPublic.model_validate(order),
    )
