from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ApiResponse
from app.db.database import get_db
from app.dependencies.auth import get_current_admin, get_current_user
from app.models.user import User
from app.schemas.coupon import (
    CouponActiveUpdate,
    CouponCreate,
    CouponPublic,
    CouponUpdate,
    UserCouponPublic,
)
from app.services.coupon import (
    CouponLimitReachedError,
    CouponNotFoundError,
    CouponUnavailableError,
    UserCouponNotFoundError,
    claim_coupon,
    create_coupon,
    list_admin_coupons,
    list_available_coupons,
    list_user_coupons,
    set_coupon_active,
    update_coupon,
    utc_now,
)

router = APIRouter(tags=["优惠券"])
CouponStatus = Literal["available", "used", "expired"]


@router.get("/api/coupons", response_model=ApiResponse, summary="查询可领取优惠券")
async def get_available_coupons(
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    coupons = await list_available_coupons(session)
    return ApiResponse.success(
        data=[CouponPublic.model_validate(coupon) for coupon in coupons]
    )


@router.post(
    "/api/coupons/{coupon_id}/claim",
    response_model=ApiResponse,
    status_code=status.HTTP_201_CREATED,
    summary="领取优惠券",
)
async def post_claim_coupon(
    coupon_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        user_coupon = await claim_coupon(session, current_user.id, coupon_id)
    except CouponNotFoundError as exc:
        raise HTTPException(status_code=404, detail="优惠券不存在") from exc
    except CouponLimitReachedError as exc:
        raise HTTPException(status_code=409, detail="已达到该优惠券的领取上限") from exc
    except CouponUnavailableError as exc:
        raise HTTPException(status_code=409, detail="优惠券已结束或已领完") from exc
    return ApiResponse.success(
        message="领取成功",
        data=UserCouponPublic(
            id=user_coupon.id,
            status=user_coupon.status,
            claimed_at=user_coupon.claimed_at,
            redeemed_at=user_coupon.redeemed_at,
            coupon=CouponPublic.model_validate(user_coupon.coupon),
        ),
    )


@router.get(
    "/api/users/me/coupons",
    response_model=ApiResponse,
    summary="查询我的优惠券",
)
async def get_user_coupons(
    coupon_status: Annotated[
        CouponStatus | None,
        Query(alias="status"),
    ] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    now = utc_now()
    user_coupons = await list_user_coupons(
        session,
        current_user.id,
        coupon_status,
    )
    return ApiResponse.success(
        data=[
            UserCouponPublic(
                id=user_coupon.id,
                status=(
                    "expired"
                    if user_coupon.status == "available"
                    and user_coupon.coupon.end_time <= now
                    else user_coupon.status
                ),
                claimed_at=user_coupon.claimed_at,
                redeemed_at=user_coupon.redeemed_at,
                coupon=CouponPublic.model_validate(user_coupon.coupon),
            )
            for user_coupon in user_coupons
        ]
    )


@router.get("/api/admin/coupons", response_model=ApiResponse, summary="商家查询优惠券")
async def get_admin_coupons(
    _admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    coupons = await list_admin_coupons(session)
    return ApiResponse.success(
        data=[CouponPublic.model_validate(coupon) for coupon in coupons]
    )


@router.post(
    "/api/admin/coupons",
    response_model=ApiResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建优惠券",
)
async def post_admin_coupon(
    coupon_data: CouponCreate,
    _admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    coupon = await create_coupon(session, coupon_data)
    return ApiResponse.success(
        message="优惠券已创建",
        data=CouponPublic.model_validate(coupon),
    )


@router.put(
    "/api/admin/coupons/{coupon_id}",
    response_model=ApiResponse,
    summary="编辑优惠券",
)
async def put_admin_coupon(
    coupon_id: int,
    coupon_data: CouponUpdate,
    _admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        coupon = await update_coupon(session, coupon_id, coupon_data)
    except CouponNotFoundError as exc:
        raise HTTPException(status_code=404, detail="优惠券不存在") from exc
    except CouponUnavailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ApiResponse.success(data=CouponPublic.model_validate(coupon))


@router.patch(
    "/api/admin/coupons/{coupon_id}/active",
    response_model=ApiResponse,
    summary="启用或停用优惠券",
)
async def patch_admin_coupon_active(
    coupon_id: int,
    update_data: CouponActiveUpdate,
    _admin=Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse:
    try:
        coupon = await set_coupon_active(
            session,
            coupon_id,
            update_data.is_active,
        )
    except CouponNotFoundError as exc:
        raise HTTPException(status_code=404, detail="优惠券不存在") from exc
    return ApiResponse.success(data=CouponPublic.model_validate(coupon))
