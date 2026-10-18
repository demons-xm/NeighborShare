import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.database import get_db
from app.models.address import Address
from app.models.admin import Admin
from app.models.category import Category
from app.models.coupon import Coupon, UserCoupon
from app.models.dish import Dish
from app.models.order import Order
from app.models.seckill import SeckillActivity
from app.models.shop import Shop
from app.models.user import User
from app.utils.token import create_access_token
import main as main_module


def test_coupon_claim_checkout_and_seckill_stock(monkeypatch):
    async def run_test():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        monkeypatch.setattr(main_module, "async_engine", engine)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        async def override_get_db():
            async with session_factory() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        main_module.app.dependency_overrides[get_db] = override_get_db
        try:
            async with main_module.app.router.lifespan_context(main_module.app):
                async with AsyncClient(
                    transport=ASGITransport(app=main_module.app),
                    base_url="http://test",
                ) as client:
                    async with session_factory() as session:
                        user = User(phone="13800138881", password_hash="unused")
                        admin = Admin(username="merchant", password_hash="unused")
                        category = Category(shop_id=1, name="主食")
                        session.add_all([user, admin, category])
                        await session.flush()
                        address = Address(
                            user_id=user.id,
                            recipient_name="测试用户",
                            phone="13800138881",
                            province="浙江省",
                            city="杭州市",
                            district="西湖区",
                            detail="文三路 1 号",
                            is_default=True,
                        )
                        dish = Dish(
                            category_id=category.id,
                            name="牛肉饭",
                            price=Decimal("10.00"),
                            stock=5,
                            is_available=True,
                        )
                        shop = await session.get(Shop, 1)
                        shop.is_open = True
                        shop.minimum_order_amount = Decimal("0.00")
                        shop.delivery_fee = Decimal("2.00")
                        session.add_all([address, dish])
                        await session.flush()
                        address_id = address.id
                        dish_id = dish.id
                        user_id = user.id
                        await session.commit()

                    user_headers = {
                        "Authorization": (
                            f"Bearer {create_access_token(str(user_id), 'user')}"
                        )
                    }
                    admin_headers = {
                        "Authorization": (
                            f"Bearer {create_access_token('merchant', 'admin')}"
                        )
                    }
                    now = datetime.now(UTC)

                    coupon_response = await client.post(
                        "/api/admin/coupons",
                        headers=admin_headers,
                        json={
                            "name": "新客立减",
                            "discount_amount": "3.00",
                            "minimum_order_amount": "15.00",
                            "total_quantity": 2,
                            "per_user_limit": 1,
                            "start_time": (now - timedelta(minutes=1)).isoformat(),
                            "end_time": (now + timedelta(hours=1)).isoformat(),
                        },
                    )
                    assert coupon_response.status_code == 201
                    coupon_id = coupon_response.json()["data"]["id"]

                    claimed = await client.post(
                        f"/api/coupons/{coupon_id}/claim",
                        headers=user_headers,
                    )
                    assert claimed.status_code == 201
                    user_coupon_id = claimed.json()["data"]["id"]
                    repeated_claim = await client.post(
                        f"/api/coupons/{coupon_id}/claim",
                        headers=user_headers,
                    )
                    assert repeated_claim.status_code == 409
                    changed_coupon = await client.put(
                        f"/api/admin/coupons/{coupon_id}",
                        headers=admin_headers,
                        json={"discount_amount": "4.00"},
                    )
                    assert changed_coupon.status_code == 409

                    await client.post(
                        "/api/cart/items",
                        headers=user_headers,
                        json={"dish_id": dish_id, "quantity": 1},
                    )
                    below_minimum = await client.post(
                        "/api/orders",
                        headers=user_headers,
                        json={
                            "address_id": address_id,
                            "user_coupon_id": user_coupon_id,
                        },
                    )
                    assert below_minimum.status_code == 409
                    await client.put(
                        f"/api/cart/items/{dish_id}",
                        headers=user_headers,
                        json={"quantity": 2},
                    )
                    checkout = await client.post(
                        "/api/orders",
                        headers=user_headers,
                        json={
                            "address_id": address_id,
                            "user_coupon_id": user_coupon_id,
                        },
                    )
                    assert checkout.status_code == 201
                    order = checkout.json()["data"]
                    assert order["dish_amount"] == "20.00"
                    assert order["discount_amount"] == "3.00"
                    assert order["total_amount"] == "19.00"

                    cancelled = await client.post(
                        f"/api/orders/{order['id']}/cancel",
                        headers=user_headers,
                    )
                    assert cancelled.status_code == 200
                    user_coupons = await client.get(
                        "/api/users/me/coupons?status=available",
                        headers=user_headers,
                    )
                    assert user_coupons.status_code == 200
                    assert user_coupons.json()["data"][0]["status"] == "available"

                    accepted_coupon_order = await client.post(
                        "/api/orders",
                        headers=user_headers,
                        json={
                            "address_id": address_id,
                            "user_coupon_id": user_coupon_id,
                        },
                    )
                    assert accepted_coupon_order.status_code == 201
                    paid_order_id = accepted_coupon_order.json()["data"]["id"]
                    accepted = await client.patch(
                        f"/api/admin/orders/{paid_order_id}/status",
                        headers=admin_headers,
                        json={"status": "pending_acceptance"},
                    )
                    assert accepted.status_code == 200
                    admin_cancelled = await client.patch(
                        f"/api/admin/orders/{paid_order_id}/status",
                        headers=admin_headers,
                        json={"status": "cancelled"},
                    )
                    assert admin_cancelled.status_code == 200
                    used_coupons = await client.get(
                        "/api/users/me/coupons?status=used",
                        headers=user_headers,
                    )
                    assert used_coupons.status_code == 200
                    assert used_coupons.json()["data"][0]["id"] == user_coupon_id

                    activity_response = await client.post(
                        "/api/admin/seckill/activities",
                        headers=admin_headers,
                        json={
                            "name": "午间限量秒杀",
                            "dish_id": dish_id,
                            "sale_price": "5.00",
                            "stock": 4,
                            "limit_per_user": 2,
                            "start_time": (now - timedelta(minutes=1)).isoformat(),
                            "end_time": (now + timedelta(hours=1)).isoformat(),
                        },
                    )
                    assert activity_response.status_code == 201
                    activity_id = activity_response.json()["data"]["id"]
                    activity_order = await client.post(
                        f"/api/seckill/activities/{activity_id}/orders",
                        headers=user_headers,
                        json={"address_id": address_id, "quantity": 2},
                    )
                    assert activity_order.status_code == 201
                    seckill_order = activity_order.json()["data"]
                    assert seckill_order["source"] == "seckill"
                    assert seckill_order["dish_amount"] == "10.00"

                    sold_out = await client.post(
                        f"/api/seckill/activities/{activity_id}/orders",
                        headers=user_headers,
                        json={"address_id": address_id, "quantity": 3},
                    )
                    assert sold_out.status_code == 409

                    over_user_limit = await client.post(
                        f"/api/seckill/activities/{activity_id}/orders",
                        headers=user_headers,
                        json={"address_id": address_id, "quantity": 1},
                    )
                    assert over_user_limit.status_code == 409
                    assert (
                        over_user_limit.json()["message"]
                        == "已达到该活动的限购数量"
                    )

                    cancelled_seckill = await client.post(
                        f"/api/orders/{seckill_order['id']}/cancel",
                        headers=user_headers,
                    )
                    assert cancelled_seckill.status_code == 200
                    retry_after_cancel = await client.post(
                        f"/api/seckill/activities/{activity_id}/orders",
                        headers=user_headers,
                        json={"address_id": address_id, "quantity": 2},
                    )
                    assert retry_after_cancel.status_code == 201
                    cancelled_retry = await client.post(
                        f"/api/orders/{retry_after_cancel.json()['data']['id']}/cancel",
                        headers=user_headers,
                    )
                    assert cancelled_retry.status_code == 200
                    async with session_factory() as session:
                        activity = await session.get(SeckillActivity, activity_id)
                        coupon = await session.get(Coupon, coupon_id)
                        user_coupon = await session.get(UserCoupon, user_coupon_id)
                        dish = await session.get(Dish, dish_id)
                        stored_order = await session.get(Order, seckill_order["id"])
                        assert activity.sold_count == 0
                        assert coupon.claimed_quantity == 1
                        assert user_coupon.status == "used"
                        assert dish.stock == 5
                        assert stored_order.status == "cancelled"

                    unauthorized = await client.post(
                        f"/api/seckill/activities/{activity_id}/orders",
                        json={"address_id": address_id},
                    )
                    assert unauthorized.status_code == 401
        finally:
            main_module.app.dependency_overrides.pop(get_db, None)
            await engine.dispose()

    asyncio.run(run_test())
