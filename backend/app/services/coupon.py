from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.coupon import Coupon, UserCoupon
from app.schemas.coupon import CouponCreate, CouponUpdate


class CouponNotFoundError(Exception):
    pass


class CouponUnavailableError(Exception):
    pass


class CouponLimitReachedError(Exception):
    pass


class UserCouponNotFoundError(Exception):
    pass


class UserCouponUnavailableError(Exception):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def list_available_coupons(session: AsyncSession) -> list[Coupon]:
    now = utc_now()
    result = await session.scalars(
        select(Coupon)
        .where(
            Coupon.is_active.is_(True),
            Coupon.start_time <= now,
            Coupon.end_time > now,
            Coupon.claimed_quantity < Coupon.total_quantity,
        )
        .order_by(Coupon.end_time, Coupon.id)
    )
    return list(result.all())


async def list_admin_coupons(session: AsyncSession) -> list[Coupon]:
    result = await session.scalars(select(Coupon).order_by(Coupon.id.desc()))
    return list(result.all())


async def create_coupon(
    session: AsyncSession,
    coupon_data: CouponCreate,
) -> Coupon:
    coupon = Coupon(**coupon_data.model_dump())
    session.add(coupon)
    await session.flush()
    return coupon


async def update_coupon(
    session: AsyncSession,
    coupon_id: int,
    coupon_data: CouponUpdate,
) -> Coupon:
    coupon = await session.scalar(
        select(Coupon).where(Coupon.id == coupon_id).with_for_update()
    )
    if coupon is None:
        raise CouponNotFoundError

    updates = coupon_data.model_dump(exclude_unset=True)
    if updates.get("total_quantity", coupon.total_quantity) < coupon.claimed_quantity:
        raise CouponUnavailableError("优惠券总量不能少于已领取数量")

    immutable_fields = {
        "discount_amount",
        "minimum_order_amount",
        "start_time",
        "end_time",
    }
    if coupon.claimed_quantity and any(
        updates.get(field, getattr(coupon, field)) != getattr(coupon, field)
        for field in immutable_fields
    ):
        raise CouponUnavailableError("优惠券已有用户领取，不能再修改面额、门槛或有效期")

    start_time = updates.get("start_time", coupon.start_time)
    end_time = updates.get("end_time", coupon.end_time)
    if end_time <= start_time:
        raise CouponUnavailableError("优惠券结束时间必须晚于开始时间")

    for field, value in updates.items():
        setattr(coupon, field, value)
    await session.flush()
    return coupon


async def set_coupon_active(
    session: AsyncSession,
    coupon_id: int,
    is_active: bool,
) -> Coupon:
    coupon = await session.get(Coupon, coupon_id)
    if coupon is None:
        raise CouponNotFoundError
    coupon.is_active = is_active
    await session.flush()
    return coupon


async def claim_coupon(
    session: AsyncSession,
    user_id: int,
    coupon_id: int,
) -> UserCoupon:
    coupon = await session.get(Coupon, coupon_id)
    if coupon is None:
        raise CouponNotFoundError

    now = utc_now()
    reserved = await session.execute(
        update(Coupon)
        .where(
            Coupon.id == coupon_id,
            Coupon.is_active.is_(True),
            Coupon.start_time <= now,
            Coupon.end_time > now,
            Coupon.claimed_quantity < Coupon.total_quantity,
        )
        .values(claimed_quantity=Coupon.claimed_quantity + 1)
    )
    if reserved.rowcount != 1:
        raise CouponUnavailableError
    coupon = await session.scalar(
        select(Coupon)
        .where(Coupon.id == coupon_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if coupon is None:
        raise CouponNotFoundError

    claimed_count = await session.scalar(
        select(func.count(UserCoupon.id)).where(
            UserCoupon.user_id == user_id,
            UserCoupon.coupon_id == coupon_id,
        )
    )
    if claimed_count is not None and claimed_count >= coupon.per_user_limit:
        raise CouponLimitReachedError

    user_coupon = UserCoupon(
        user_id=user_id,
        coupon_id=coupon_id,
        status="available",
        claimed_at=now,
    )
    session.add(user_coupon)
    await session.flush()
    await session.refresh(user_coupon, attribute_names=["coupon"])
    return user_coupon


async def list_user_coupons(
    session: AsyncSession,
    user_id: int,
    status_filter: str | None = None,
) -> list[UserCoupon]:
    now = utc_now()
    query = (
        select(UserCoupon)
        .join(Coupon)
        .where(UserCoupon.user_id == user_id)
        .options(selectinload(UserCoupon.coupon))
        .order_by(UserCoupon.id.desc())
    )
    if status_filter == "used":
        query = query.where(UserCoupon.status == "used")
    elif status_filter == "expired":
        query = query.where(
            UserCoupon.status == "available",
            Coupon.end_time <= now,
        )
    elif status_filter == "available":
        query = query.where(
            UserCoupon.status == "available",
            Coupon.end_time > now,
        )
    result = await session.scalars(query)
    return list(result.all())


async def get_user_coupon_for_update(
    session: AsyncSession,
    user_id: int,
    user_coupon_id: int,
) -> UserCoupon:
    user_coupon = await session.scalar(
        select(UserCoupon)
        .where(
            UserCoupon.id == user_coupon_id,
            UserCoupon.user_id == user_id,
        )
        .with_for_update()
    )
    if user_coupon is None:
        raise UserCouponNotFoundError
    if user_coupon.status != "available":
        raise UserCouponUnavailableError("这张优惠券已使用")

    await session.refresh(user_coupon, attribute_names=["coupon"])
    now = utc_now()
    coupon = user_coupon.coupon
    if coupon.start_time > now or coupon.end_time <= now:
        raise UserCouponUnavailableError("这张优惠券已失效")
    return user_coupon
