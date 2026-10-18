from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import config
# 一定要每次从models里面导入模型，用于创建表
from app.models.user import User
from app.models.admin import Admin
from app.models.address import Address
from app.models.shop import Shop
from app.models.category import Category
from app.models.dish import Dish
from app.models.cart import Cart, CartItem
from app.models.order import Order
from app.models.order_item import OrderItem

from app.common.exceptions import register_exception_handlers
from app.db.database import Base, async_engine
from app.routers import router as api_router
from app.services.admin import ensure_bootstrap_admin
from app.services.shop import get_shop


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(async_engine, expire_on_commit=False)
    async with session_factory() as session:
        await get_shop(session)
        await ensure_bootstrap_admin(
            session,
            config.ADMIN_USERNAME,
            config.ADMIN_PASSWORD,
        )
        await session.commit()
    yield


app = FastAPI(title="NeighborShare API", lifespan=lifespan)
register_exception_handlers(app)
app.include_router(api_router)