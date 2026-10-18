from fastapi import APIRouter

from app.routers.address import router as address_router
from app.routers.admin_auth import router as admin_auth_router
from app.routers.auth import router as auth_router
from app.routers.cart import router as cart_router
from app.routers.category import router as category_router
from app.routers.coupon import router as coupon_router
from app.routers.dish import router as dish_router
from app.routers.order import router as order_router
from app.routers.shop import router as shop_router
from app.routers.seckill import router as seckill_router
from app.routers.statistics import router as statistics_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(admin_auth_router)
router.include_router(address_router)
router.include_router(cart_router)
router.include_router(shop_router)
router.include_router(seckill_router)
router.include_router(category_router)
router.include_router(coupon_router)
router.include_router(dish_router)
router.include_router(order_router)
router.include_router(statistics_router)