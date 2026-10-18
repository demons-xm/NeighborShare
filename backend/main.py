from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import config
from app.common.exceptions import register_exception_handlers
from app.db.database import Base, async_engine
from app.models import (
    Address,
    Admin,
    Cart,
    CartItem,
    Category,
    Coupon,
    Dish,
    Order,
    OrderItem,
    SeckillActivity,
    Shop,
    User,
    UserCoupon,
)
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