from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.dish import Dish
from app.schemas.category import CategoryCreate, CategoryUpdate

SHOP_ID = 1


class CategoryNotFoundError(Exception):
    pass


class CategoryHasDishesError(Exception):
    pass


async def list_categories(session: AsyncSession) -> list[Category]:
    result = await session.scalars(
        select(Category)
        .where(Category.shop_id == SHOP_ID)
        .order_by(Category.sort_order.asc(), Category.id.asc())
    )
    return list(result.all())


async def create_category(
    session: AsyncSession,
    category_data: CategoryCreate,
) -> Category:
    category = Category(shop_id=SHOP_ID, **category_data.model_dump())
    session.add(category)
    await session.flush()
    return category


async def update_category(
    session: AsyncSession,
    category_id: int,
    category_data: CategoryUpdate,
) -> Category:
    category = await _get_category(session, category_id)
    for field, value in category_data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    await session.flush()
    return category


async def delete_category(session: AsyncSession, category_id: int) -> None:
    category = await _get_category(session, category_id)
    has_dishes = await session.scalar(
        select(Dish.id).where(Dish.category_id == category_id).limit(1)
    )
    if has_dishes is not None:
        raise CategoryHasDishesError
    await session.delete(category)
    await session.flush()


async def _get_category(session: AsyncSession, category_id: int) -> Category:
    category = await session.scalar(
        select(Category).where(
            Category.id == category_id,
            Category.shop_id == SHOP_ID,
        )
    )
    if category is None:
        raise CategoryNotFoundError
    return category
