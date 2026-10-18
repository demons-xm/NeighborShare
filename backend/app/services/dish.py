from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.category import Category
from app.models.cart import CartItem
from app.models.dish import Dish
from app.models.order_item import OrderItem
from app.schemas.dish import DishCreate, DishUpdate

SHOP_ID = 1


class DishNotFoundError(Exception):
    pass


class DishCategoryNotFoundError(Exception):
    pass


class DishUnavailableError(Exception):
    pass


class InsufficientStockError(Exception):
    pass


async def list_available_dishes(
    session: AsyncSession,
    category_id: int | None = None,
) -> list[Dish]:
    query = (
        select(Dish)
        .join(Category)
        .where(Category.shop_id == SHOP_ID, Dish.is_available.is_(True))
        .options(selectinload(Dish.category))
        .order_by(Category.sort_order.asc(), Dish.id.asc())
    )
    if category_id is not None:
        query = query.where(Dish.category_id == category_id)
    result = await session.scalars(query)
    return list(result.all())


async def get_available_dish(session: AsyncSession, dish_id: int) -> Dish:
    dish = await session.scalar(
        select(Dish)
        .join(Category)
        .where(
            Dish.id == dish_id,
            Dish.is_available.is_(True),
            Category.shop_id == SHOP_ID,
        )
        .options(selectinload(Dish.category))
    )
    if dish is None:
        raise DishNotFoundError
    return dish


async def list_admin_dishes(
    session: AsyncSession,
    category_id: int | None = None,
    is_available: bool | None = None,
) -> list[Dish]:
    query = (
        select(Dish)
        .join(Category)
        .where(Category.shop_id == SHOP_ID)
        .options(selectinload(Dish.category))
        .order_by(Category.sort_order.asc(), Dish.id.asc())
    )
    if category_id is not None:
        query = query.where(Dish.category_id == category_id)
    if is_available is not None:
        query = query.where(Dish.is_available.is_(is_available))
    result = await session.scalars(query)
    return list(result.all())


async def create_dish(session: AsyncSession, dish_data: DishCreate) -> Dish:
    await _ensure_category(session, dish_data.category_id)
    dish = Dish(**dish_data.model_dump())
    session.add(dish)
    await session.flush()
    await session.refresh(dish, attribute_names=["category"])
    return dish


async def update_dish(
    session: AsyncSession,
    dish_id: int,
    dish_data: DishUpdate,
) -> Dish:
    dish = await _get_admin_dish(session, dish_id)
    changes = dish_data.model_dump(exclude_unset=True)
    category_id = changes.get("category_id")
    if category_id is not None:
        await _ensure_category(session, category_id)
    for field, value in changes.items():
        setattr(dish, field, value)
    await session.flush()
    await session.refresh(dish, attribute_names=["category"])
    return dish


async def set_dish_availability(
    session: AsyncSession,
    dish_id: int,
    is_available: bool,
) -> Dish:
    dish = await _get_admin_dish(session, dish_id)
    dish.is_available = is_available
    await session.flush()
    return dish


async def delete_dish(session: AsyncSession, dish_id: int) -> None:
    dish = await _get_admin_dish(session, dish_id)
    await session.execute(
        OrderItem.__table__.update()
        .where(OrderItem.dish_id == dish_id)
        .values(dish_id=None)
    )
    await session.execute(
        CartItem.__table__.delete().where(CartItem.dish_id == dish_id)
    )
    await session.delete(dish)
    await session.flush()


async def validate_dish_for_order(
    session: AsyncSession,
    dish_id: int,
    quantity: int,
) -> Dish:
    if quantity <= 0:
        raise ValueError("菜品数量必须大于 0")
    dish = await session.scalar(
        select(Dish)
        .join(Category)
        .where(
            Dish.id == dish_id,
            Category.shop_id == SHOP_ID,
        )
        .options(selectinload(Dish.category))
        .with_for_update()
    )
    if dish is None or not dish.is_available:
        raise DishUnavailableError
    if dish.stock < quantity:
        raise InsufficientStockError
    return dish


async def _ensure_category(session: AsyncSession, category_id: int) -> None:
    category = await session.scalar(
        select(Category.id).where(
            Category.id == category_id,
            Category.shop_id == SHOP_ID,
        )
    )
    if category is None:
        raise DishCategoryNotFoundError


async def _get_admin_dish(session: AsyncSession, dish_id: int) -> Dish:
    dish = await session.scalar(
        select(Dish)
        .join(Category)
        .where(Dish.id == dish_id, Category.shop_id == SHOP_ID)
        .options(selectinload(Dish.category))
    )
    if dish is None:
        raise DishNotFoundError
    return dish
