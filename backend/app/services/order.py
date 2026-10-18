from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.address import Address
from app.models.cart import Cart, CartItem
from app.models.category import Category
from app.models.dish import Dish
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.shop import Shop
from app.models.user import User
from app.schemas.order import OrderCreate, OrderStatus

SHOP_ID = 1
ADMIN_TRANSITIONS: dict[str, set[str]] = {
    "pending_payment": {"pending_acceptance"},
    "pending_acceptance": {"pending_delivery", "cancelled"},
    "pending_delivery": {"completed", "cancelled"},
}


class OrderAddressNotFoundError(Exception):
    pass


class EmptyCartError(Exception):
    pass


class ShopClosedError(Exception):
    pass


class MinimumOrderAmountError(Exception):
    pass


class OrderNotFoundError(Exception):
    pass


class OrderStatusConflictError(Exception):
    pass


async def create_order(
    session: AsyncSession,
    user_id: int,
    order_data: OrderCreate,
) -> Order:
    await session.scalar(select(User.id).where(User.id == user_id).with_for_update())

    address = await session.scalar(
        select(Address).where(
            Address.id == order_data.address_id,
            Address.user_id == user_id,
        )
    )
    if address is None:
        raise OrderAddressNotFoundError

    shop = await session.scalar(
        select(Shop).where(Shop.id == SHOP_ID).with_for_update()
    )
    if shop is None or not shop.is_open:
        raise ShopClosedError

    cart = await session.scalar(
        select(Cart).where(Cart.user_id == user_id).with_for_update()
    )
    if cart is None:
        raise EmptyCartError

    cart_items = list(
        (
            await session.scalars(
                select(CartItem)
                .where(CartItem.cart_id == cart.id)
                .order_by(CartItem.dish_id)
                .with_for_update()
            )
        ).all()
    )
    if not cart_items:
        raise EmptyCartError

    dishes: dict[int, Dish] = {}
    for cart_item in cart_items:
        dish = await session.scalar(
            select(Dish)
            .where(Dish.id == cart_item.dish_id)
            .with_for_update()
        )
        if dish is None or not dish.is_available:
            raise OrderStatusConflictError("购物车中存在已下架或已删除的菜品")
        if dish.stock < cart_item.quantity:
            raise OrderStatusConflictError(f"菜品“{dish.name}”库存不足")
        dishes[dish.id] = dish

    category_ids = {dish.category_id for dish in dishes.values()}
    categories = await session.scalars(
        select(Category).where(
            Category.id.in_(category_ids),
            Category.shop_id == SHOP_ID,
        )
    )
    category_names = {category.id: category.name for category in categories}
    if len(category_names) != len(category_ids):
        raise OrderStatusConflictError("购物车中存在无效分类的菜品")

    dish_amount = sum(
        (
            dishes[item.dish_id].price * item.quantity
            for item in cart_items
        ),
        start=Decimal("0.00"),
    )
    if dish_amount < shop.minimum_order_amount:
        raise MinimumOrderAmountError

    delivery_fee = shop.delivery_fee
    order = Order(
        order_no=uuid4().hex,
        user_id=user_id,
        status="pending_payment",
        recipient_name=address.recipient_name,
        recipient_phone=address.phone,
        province=address.province,
        city=address.city,
        district=address.district,
        address_detail=address.detail,
        dish_amount=dish_amount,
        delivery_fee=delivery_fee,
        total_amount=dish_amount + delivery_fee,
    )
    for item in cart_items:
        dish = dishes[item.dish_id]
        dish.stock -= item.quantity
        order.items.append(
            OrderItem(
                dish_id=dish.id,
                dish_name=dish.name,
                dish_image_url=dish.image_url,
                category_name=category_names[dish.category_id],
                unit_price=dish.price,
                quantity=item.quantity,
                subtotal=dish.price * item.quantity,
            )
        )

    session.add(order)
    await session.flush()
    await session.refresh(order, attribute_names=["items"])
    return order


async def list_user_orders(
    session: AsyncSession,
    user_id: int,
    offset: int = 0,
    limit: int = 20,
) -> list[Order]:
    result = await session.scalars(
        select(Order)
        .where(Order.user_id == user_id)
        .options(selectinload(Order.items))
        .order_by(Order.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.all())


async def get_user_order(
    session: AsyncSession,
    user_id: int,
    order_id: int,
) -> Order:
    order = await session.scalar(
        select(Order)
        .where(Order.id == order_id, Order.user_id == user_id)
        .options(selectinload(Order.items))
    )
    if order is None:
        raise OrderNotFoundError
    return order


async def cancel_user_order(
    session: AsyncSession,
    user_id: int,
    order_id: int,
) -> Order:
    order = await _get_order_for_update(session, order_id, user_id=user_id)
    if order is None:
        raise OrderNotFoundError
    if order.status != "pending_payment":
        raise OrderStatusConflictError("只有待付款订单可以取消")

    await _restore_order_stock(session, order)
    order.status = "cancelled"
    await session.flush()
    return order


async def simulate_user_payment(
    session: AsyncSession,
    user_id: int,
    order_id: int,
) -> Order:
    order = await _get_order_for_update(session, order_id, user_id=user_id)
    if order is None:
        raise OrderNotFoundError
    if order.status != "pending_payment":
        raise OrderStatusConflictError("只有待付款订单可以支付")

    order.status = "pending_acceptance"
    await session.flush()
    return order


async def confirm_user_receipt(
    session: AsyncSession,
    user_id: int,
    order_id: int,
) -> Order:
    order = await _get_order_for_update(session, order_id, user_id=user_id)
    if order is None:
        raise OrderNotFoundError
    if order.status != "pending_delivery":
        raise OrderStatusConflictError("只有配送中的订单可以确认收货")

    order.status = "completed"
    await session.flush()
    return order


async def list_admin_orders(
    session: AsyncSession,
    status_filter: OrderStatus | None = None,
    offset: int = 0,
    limit: int = 20,
) -> list[Order]:
    query = select(Order).options(selectinload(Order.items))
    if status_filter is not None:
        query = query.where(Order.status == status_filter)
    result = await session.scalars(
        query.order_by(Order.id.desc()).offset(offset).limit(limit)
    )
    return list(result.all())


async def update_order_status(
    session: AsyncSession,
    order_id: int,
    new_status: OrderStatus,
) -> Order:
    order = await _get_order_for_update(session, order_id)
    if order is None:
        raise OrderNotFoundError
    if new_status not in ADMIN_TRANSITIONS.get(order.status, set()):
        raise OrderStatusConflictError("不允许的订单状态流转")

    if new_status == "cancelled":
        await _restore_order_stock(session, order)
    order.status = new_status
    await session.flush()
    return order


async def _get_order_for_update(
    session: AsyncSession,
    order_id: int,
    user_id: int | None = None,
) -> Order | None:
    query = select(Order).where(Order.id == order_id)
    if user_id is not None:
        query = query.where(Order.user_id == user_id)
    order = await session.scalar(query.with_for_update())
    if order is not None:
        await session.refresh(order, attribute_names=["items"])
    return order


async def _restore_order_stock(session: AsyncSession, order: Order) -> None:
    dish_ids = sorted(
        {item.dish_id for item in order.items if item.dish_id is not None}
    )
    for dish_id in dish_ids:
        dish = await session.scalar(
            select(Dish).where(Dish.id == dish_id).with_for_update()
        )
        if dish is None:
            continue
        dish.stock += sum(
            item.quantity for item in order.items if item.dish_id == dish_id
        )
