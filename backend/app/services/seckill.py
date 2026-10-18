from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.address import Address
from app.models.category import Category
from app.models.dish import Dish
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.seckill import SeckillActivity
from app.models.shop import Shop
from app.models.user import User
from app.schemas.order import SeckillOrderCreate
from app.schemas.seckill import SeckillActivityCreate, SeckillActivityUpdate
from app.services.coupon import utc_now
from app.services.shop import SHOP_ID


class SeckillActivityNotFoundError(Exception):
    pass


class SeckillActivityUnavailableError(Exception):
    pass


class SeckillActivityLimitError(Exception):
    pass


class SeckillDishUnavailableError(Exception):
    pass


class SeckillAddressNotFoundError(Exception):
    pass


class SeckillShopClosedError(Exception):
    pass


def activity_status(activity: SeckillActivity, now: datetime | None = None) -> str:
    now = now or utc_now()
    if not activity.is_active:
        return "inactive"
    if activity.end_time <= now:
        return "ended"
    if activity.sold_count >= activity.stock:
        return "sold_out"
    if activity.start_time > now:
        return "upcoming"
    return "active"


def activity_payload(activity: SeckillActivity) -> dict[str, object]:
    return {
        "id": activity.id,
        "name": activity.name,
        "dish_id": activity.dish_id,
        "dish_name": activity.dish.name,
        "dish_image_url": activity.dish.image_url,
        "original_price": activity.dish.price,
        "sale_price": activity.sale_price,
        "stock": activity.stock,
        "sold_count": activity.sold_count,
        "remaining_stock": max(activity.stock - activity.sold_count, 0),
        "limit_per_user": activity.limit_per_user,
        "start_time": activity.start_time,
        "end_time": activity.end_time,
        "is_active": activity.is_active,
        "status": activity_status(activity),
    }


async def list_public_activities(
    session: AsyncSession,
) -> list[SeckillActivity]:
    now = utc_now()
    result = await session.scalars(
        select(SeckillActivity)
        .join(Dish, SeckillActivity.dish_id == Dish.id)
        .where(
            SeckillActivity.is_active.is_(True),
            SeckillActivity.end_time > now,
            SeckillActivity.sold_count < SeckillActivity.stock,
            SeckillActivity.sale_price <= Dish.price,
        )
        .options(selectinload(SeckillActivity.dish))
        .order_by(SeckillActivity.start_time, SeckillActivity.id)
    )
    return list(result.all())


async def list_admin_activities(
    session: AsyncSession,
) -> list[SeckillActivity]:
    result = await session.scalars(
        select(SeckillActivity)
        .options(selectinload(SeckillActivity.dish))
        .order_by(SeckillActivity.id.desc())
    )
    return list(result.all())


async def get_activity(
    session: AsyncSession,
    activity_id: int,
) -> SeckillActivity:
    activity = await session.scalar(
        select(SeckillActivity)
        .where(SeckillActivity.id == activity_id)
        .options(selectinload(SeckillActivity.dish))
    )
    if activity is None:
        raise SeckillActivityNotFoundError
    return activity


async def create_activity(
    session: AsyncSession,
    activity_data: SeckillActivityCreate,
) -> SeckillActivity:
    dish = await _get_seckill_dish(session, activity_data.dish_id)
    if activity_data.sale_price > dish.price:
        raise SeckillDishUnavailableError("秒杀价不能高于商品原价")
    if activity_data.stock > dish.stock:
        raise SeckillDishUnavailableError("秒杀库存不能超过当前商品库存")
    activity = SeckillActivity(**activity_data.model_dump())
    session.add(activity)
    await session.flush()
    await session.refresh(activity, attribute_names=["dish"])
    return activity


async def update_activity(
    session: AsyncSession,
    activity_id: int,
    activity_data: SeckillActivityUpdate,
) -> SeckillActivity:
    activity = await session.scalar(
        select(SeckillActivity)
        .where(SeckillActivity.id == activity_id)
        .with_for_update()
    )
    if activity is None:
        raise SeckillActivityNotFoundError

    updates = activity_data.model_dump(exclude_unset=True)
    stock = updates.get("stock", activity.stock)
    if stock < activity.sold_count:
        raise SeckillActivityUnavailableError("活动库存不能少于已售数量")
    start_time = updates.get("start_time", activity.start_time)
    end_time = updates.get("end_time", activity.end_time)
    if end_time <= start_time:
        raise SeckillActivityUnavailableError("秒杀结束时间必须晚于开始时间")

    if "sale_price" in updates:
        await session.refresh(activity, attribute_names=["dish"])
        if updates["sale_price"] > activity.dish.price:
            raise SeckillActivityUnavailableError("秒杀价不能高于商品原价")
    if "stock" in updates:
        await session.refresh(activity, attribute_names=["dish"])
        if updates["stock"] > activity.dish.stock + activity.sold_count:
            raise SeckillActivityUnavailableError(
                "活动库存不能超过该商品当前可售库存"
            )
    for field, value in updates.items():
        setattr(activity, field, value)
    await session.flush()
    await session.refresh(activity, attribute_names=["dish"])
    return activity


async def set_activity_active(
    session: AsyncSession,
    activity_id: int,
    is_active: bool,
) -> SeckillActivity:
    activity = await session.scalar(
        select(SeckillActivity)
        .where(SeckillActivity.id == activity_id)
        .options(selectinload(SeckillActivity.dish))
    )
    if activity is None:
        raise SeckillActivityNotFoundError
    activity.is_active = is_active
    await session.flush()
    return activity


async def create_seckill_order(
    session: AsyncSession,
    user_id: int,
    activity_id: int,
    order_data: SeckillOrderCreate,
) -> Order:
    await session.scalar(select(User.id).where(User.id == user_id).with_for_update())
    activity = await session.scalar(
        select(SeckillActivity)
        .where(SeckillActivity.id == activity_id)
        .with_for_update()
    )
    if activity is None:
        raise SeckillActivityNotFoundError

    now = utc_now()
    if (
        not activity.is_active
        or activity.start_time > now
        or activity.end_time <= now
    ):
        raise SeckillActivityUnavailableError("秒杀活动当前不可参与")
    if activity.sold_count + order_data.quantity > activity.stock:
        raise SeckillActivityUnavailableError("秒杀库存不足")

    activity_update = await session.execute(
        update(SeckillActivity)
        .where(
            SeckillActivity.id == activity_id,
            SeckillActivity.is_active.is_(True),
            SeckillActivity.start_time <= now,
            SeckillActivity.end_time > now,
            SeckillActivity.sold_count + order_data.quantity
            <= SeckillActivity.stock,
        )
        .values(sold_count=SeckillActivity.sold_count + order_data.quantity)
    )
    if activity_update.rowcount != 1:
        raise SeckillActivityUnavailableError("秒杀库存不足")

    user_quantity = await session.scalar(
        select(func.coalesce(func.sum(OrderItem.quantity), 0))
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Order.user_id == user_id,
            Order.seckill_activity_id == activity_id,
            Order.status != "cancelled",
        )
    )
    if (user_quantity or 0) + order_data.quantity > activity.limit_per_user:
        raise SeckillActivityLimitError

    address = await session.scalar(
        select(Address).where(
            Address.id == order_data.address_id,
            Address.user_id == user_id,
        )
    )
    if address is None:
        raise SeckillAddressNotFoundError

    shop = await session.scalar(
        select(Shop).where(Shop.id == SHOP_ID).with_for_update()
    )
    if shop is None or not shop.is_open:
        raise SeckillShopClosedError

    dish = await _get_seckill_dish(session, activity.dish_id, lock=True)
    if activity.sale_price > dish.price:
        raise SeckillDishUnavailableError(
            "活动价格高于当前商品原价，暂时无法下单"
        )
    if dish.stock < order_data.quantity:
        raise SeckillDishUnavailableError("商品库存不足")

    dish_update = await session.execute(
        update(Dish)
        .where(
            Dish.id == dish.id,
            Dish.is_available.is_(True),
            Dish.stock >= order_data.quantity,
        )
        .values(stock=Dish.stock - order_data.quantity)
    )
    if dish_update.rowcount != 1:
        raise SeckillDishUnavailableError("商品库存不足或已下架")

    dish_amount = activity.sale_price * order_data.quantity
    order = Order(
        order_no=uuid4().hex,
        user_id=user_id,
        status="pending_payment",
        source="seckill",
        seckill_activity_id=activity.id,
        recipient_name=address.recipient_name,
        recipient_phone=address.phone,
        province=address.province,
        city=address.city,
        district=address.district,
        address_detail=address.detail,
        dish_amount=dish_amount,
        discount_amount=Decimal("0.00"),
        delivery_fee=shop.delivery_fee,
        total_amount=dish_amount + shop.delivery_fee,
    )
    order.items.append(
        OrderItem(
            dish_id=dish.id,
            dish_name=dish.name,
            dish_image_url=dish.image_url,
            category_name=dish.category.name,
            unit_price=activity.sale_price,
            quantity=order_data.quantity,
            subtotal=dish_amount,
        )
    )
    session.add(order)
    await session.flush()
    await session.refresh(order, attribute_names=["items"])
    return order


async def _get_seckill_dish(
    session: AsyncSession,
    dish_id: int,
    *,
    lock: bool = False,
) -> Dish:
    query = (
        select(Dish)
        .join(Category)
        .where(Dish.id == dish_id, Category.shop_id == SHOP_ID)
        .options(selectinload(Dish.category))
    )
    if lock:
        query = query.with_for_update()
    dish = await session.scalar(query)
    if dish is None or not dish.is_available:
        raise SeckillDishUnavailableError("秒杀商品不存在或已下架")
    return dish
