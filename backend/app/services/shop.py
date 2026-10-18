from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shop import Shop
from app.schemas.shop import ShopUpdate

SHOP_ID = 1


async def get_shop(session: AsyncSession) -> Shop:
    shop = await session.get(Shop, SHOP_ID)
    if shop is None:
        shop = Shop(id=SHOP_ID)
        session.add(shop)
        await session.flush()
    return shop


async def update_shop(session: AsyncSession, shop_data: ShopUpdate) -> Shop:
    shop = await session.scalar(
        select(Shop).where(Shop.id == SHOP_ID).with_for_update()
    )
    if shop is None:
        shop = Shop(id=SHOP_ID)
        session.add(shop)
        await session.flush()

    for field, value in shop_data.model_dump(exclude_unset=True).items():
        setattr(shop, field, value)
    await session.flush()
    return shop
