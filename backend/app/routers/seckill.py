from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ApiResponse
from app.db.database import get_db
from app.dependencies.auth import get_current_admin, get_current_user
from app.models.user import User
from app.schemas.order import OrderPublic, SeckillOrderCreate
from app.schemas.seckill import (
    SeckillActiveUpdate,
    SeckillActivityCreate,
    SeckillActivityPublic,
    SeckillActivityUpdate,
)
from app.services.seckill import (
    SeckillActivityLimitError,
    SeckillActivityNotFoundError,
    SeckillActivityUnavailableError,
    SeckillAddressNotFoundError,
    SeckillDishUnavailableError,
    SeckillShopClosedError,
    activity_payload,
    create_activity,
    create_seckill_order,
    get_activity,
    list_admin_activities,
    list_public_activities,
    set_activity_active,
    update_activity,
)

router = APIRouter(tags=["秒杀"])


@router.get(
    "/api/seckill/activities",
    response_model=ApiResponse,
    summary="查询秒杀活动",
)
async def get_seckill_activities(
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    activities = await list_public_activities(session)
    return ApiResponse.success(
        data=[
            SeckillActivityPublic.model_validate(activity_payload(activity))
            for activity in activities
        ]
    )


@router.get(
    "/api/seckill/activities/{activity_id}",
    response_model=ApiResponse,
    summary="查询秒杀活动详情",
)
async def get_seckill_activity(
    activity_id: int,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        activity = await get_activity(session, activity_id)
    except SeckillActivityNotFoundError as exc:
        raise HTTPException(status_code=404, detail="秒杀活动不存在") from exc
    return ApiResponse.success(
        data=SeckillActivityPublic.model_validate(activity_payload(activity))
    )


@router.post(
    "/api/seckill/activities/{activity_id}/orders",
    response_model=ApiResponse,
    status_code=status.HTTP_201_CREATED,
    summary="参与秒杀并创建订单",
)
async def post_seckill_order(
    activity_id: int,
    order_data: SeckillOrderCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        order = await create_seckill_order(
            session,
            current_user.id,
            activity_id,
            order_data,
        )
    except SeckillActivityNotFoundError as exc:
        raise HTTPException(status_code=404, detail="秒杀活动不存在") from exc
    except SeckillAddressNotFoundError as exc:
        raise HTTPException(status_code=404, detail="收货地址不存在") from exc
    except SeckillActivityLimitError as exc:
        raise HTTPException(status_code=409, detail="已达到该活动的限购数量") from exc
    except (
        SeckillActivityUnavailableError,
        SeckillDishUnavailableError,
    ) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SeckillShopClosedError as exc:
        raise HTTPException(status_code=409, detail="店铺当前未营业") from exc
    return ApiResponse.success(
        message="秒杀订单创建成功",
        data=OrderPublic.model_validate(order),
    )


@router.get(
    "/api/admin/seckill/activities",
    response_model=ApiResponse,
    summary="商家查询秒杀活动",
)
async def get_admin_seckill_activities(
    _admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    activities = await list_admin_activities(session)
    return ApiResponse.success(
        data=[
            SeckillActivityPublic.model_validate(activity_payload(activity))
            for activity in activities
        ]
    )


@router.post(
    "/api/admin/seckill/activities",
    response_model=ApiResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建秒杀活动",
)
async def post_admin_seckill_activity(
    activity_data: SeckillActivityCreate,
    _admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        activity = await create_activity(session, activity_data)
    except SeckillDishUnavailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ApiResponse.success(
        message="秒杀活动已创建",
        data=SeckillActivityPublic.model_validate(activity_payload(activity)),
    )


@router.put(
    "/api/admin/seckill/activities/{activity_id}",
    response_model=ApiResponse,
    summary="编辑秒杀活动",
)
async def put_admin_seckill_activity(
    activity_id: int,
    activity_data: SeckillActivityUpdate,
    _admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        activity = await update_activity(session, activity_id, activity_data)
    except SeckillActivityNotFoundError as exc:
        raise HTTPException(status_code=404, detail="秒杀活动不存在") from exc
    except SeckillActivityUnavailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ApiResponse.success(
        data=SeckillActivityPublic.model_validate(activity_payload(activity))
    )


@router.patch(
    "/api/admin/seckill/activities/{activity_id}/active",
    response_model=ApiResponse,
    summary="启用或停止秒杀活动",
)
async def patch_admin_seckill_active(
    activity_id: int,
    update_data: SeckillActiveUpdate,
    _admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        activity = await set_activity_active(
            session,
            activity_id,
            update_data.is_active,
        )
    except SeckillActivityNotFoundError as exc:
        raise HTTPException(status_code=404, detail="秒杀活动不存在") from exc
    return ApiResponse.success(
        data=SeckillActivityPublic.model_validate(activity_payload(activity))
    )
