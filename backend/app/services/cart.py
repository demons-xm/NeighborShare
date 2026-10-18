from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.cart import Cart, CartItem
from app.models.category import Category
from app.models.dish import Dish
from app.models.user import User
from app.schemas.cart import CartItemAdd, CartPublic
from app.schemas.dish import DishPublic

SHOP_ID = 1


class CartDishNotFoundError(Exception):
    pass


class CartDishUnavailableError(Exception):
    pass


class CartItemNotFoundError(Exception):
    pass


async def get_cart(session: AsyncSession, user_id: int) -> CartPublic:
    cart = await session.scalar(
        select(Cart)
        .where(Cart.user_id == user_id)
        .options(
            selectinload(Cart.items)
            .joinedload(CartItem.dish)
            .joinedload(Dish.category)
        )
    )
    return _serialize_cart(cart.items if cart is not None else [])


async def add_cart_item(
    session: AsyncSession,
    user_id: int,
    item_data: CartItemAdd,
) -> CartPublic:
    cart = await _get_or_create_cart(session, user_id)
    dish = await _get_dish(session, item_data.dish_id)
    if not dish.is_available:
        raise CartDishUnavailableError

    item = await session.scalar(
        select(CartItem).where(
            CartItem.cart_id == cart.id,
            CartItem.dish_id == dish.id,
        )
    )
    if item is None:
        session.add(
            CartItem(
                cart_id=cart.id,
                dish_id=dish.id,
                quantity=item_data.quantity,
                dish=dish,
            )
        )
    else:
        item.quantity += item_data.quantity
    await session.flush()
    return await get_cart(session, user_id)


async def update_cart_item_quantity(
    session: AsyncSession,
    user_id: int,
    dish_id: int,
    quantity: int,
) -> CartPublic:
    await _lock_user(session, user_id)
    cart = await _get_existing_cart(session, user_id)
    item = None
    if cart is not None:
        item = await session.scalar(
            select(CartItem).where(
                CartItem.cart_id == cart.id,
                CartItem.dish_id == dish_id,
            )
        )
    if item is None:
        raise CartItemNotFoundError
    item.quantity = quantity
    await session.flush()
    return await get_cart(session, user_id)


async def remove_cart_item(
    session: AsyncSession,
    user_id: int,
    dish_id: int,
) -> CartPublic:
    await _lock_user(session, user_id)
    cart = await _get_existing_cart(session, user_id)
    item = None
    if cart is not None:
        item = await session.scalar(
            select(CartItem).where(
                CartItem.cart_id == cart.id,
                CartItem.dish_id == dish_id,
            )
        )
    if item is None:
        raise CartItemNotFoundError
    await session.delete(item)
    await session.flush()
    return await get_cart(session, user_id)


async def clear_cart(session: AsyncSession, user_id: int) -> CartPublic:
    await _lock_user(session, user_id)
    cart = await _get_existing_cart(session, user_id)
    if cart is not None:
        await session.execute(
            CartItem.__table__.delete().where(CartItem.cart_id == cart.id)
        )
    return _serialize_cart([])


async def _get_or_create_cart(session: AsyncSession, user_id: int) -> Cart:
    await _lock_user(session, user_id)
    cart = await _get_existing_cart(session, user_id)
    if cart is None:
        cart = Cart(user_id=user_id)
        session.add(cart)
        await session.flush()
    return cart


async def _lock_user(session: AsyncSession, user_id: int) -> None:
    await session.scalar(
        select(User.id).where(User.id == user_id).with_for_update()
    )


async def _get_existing_cart(
    session: AsyncSession,
    user_id: int,
) -> Cart | None:
    return await session.scalar(select(Cart).where(Cart.user_id == user_id))


async def _get_dish(session: AsyncSession, dish_id: int) -> Dish:
    dish = await session.scalar(
        select(Dish)
        .join(Category)
        .where(Dish.id == dish_id, Category.shop_id == SHOP_ID)
        .options(joinedload(Dish.category))
    )
    if dish is None:
        raise CartDishNotFoundError
    return dish


def _serialize_cart(items: list[CartItem]) -> CartPublic:
    return CartPublic(
        items=[
            {
                "dish_id": item.dish_id,
                "quantity": item.quantity,
                "dish": DishPublic.model_validate(item.dish),
            }
            for item in items
        ],
        total_quantity=sum(item.quantity for item in items),
        total_amount=sum(
            (item.dish.price * item.quantity for item in items),
            start=Decimal("0.00"),
        ),
    )
