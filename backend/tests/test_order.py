import asyncio
from decimal import Decimal

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.database import get_db
from app.models.address import Address
from app.models.admin import Admin
from app.models.category import Category
from app.models.dish import Dish
from app.models.order import Order
from app.models.shop import Shop
from app.models.user import User
from app.utils.token import create_access_token
import main as main_module


def test_order_checkout_snapshots_cancellation_and_status_flow(monkeypatch):
    openapi = main_module.app.openapi()
    assert openapi["paths"]["/api/orders"]["post"]["security"] == [
        {"HTTPBearer": []}
    ]
    assert openapi["paths"]["/api/admin/orders"]["get"]["security"] == [
        {"HTTPBearer": []}
    ]
    assert openapi["paths"]["/api/admin/orders/{order_id}/status"]["patch"][
        "security"
    ] == [{"HTTPBearer": []}]

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
                    first_user = User(phone="13800138021", password_hash="unused")
                    second_user = User(phone="13800138022", password_hash="unused")
                    admin = Admin(username="admin-1", password_hash="unused")
                    category = Category(shop_id=1, name="主食")
                    async with session_factory() as session:
                        session.add_all(
                            [first_user, second_user, admin, category]
                        )
                        await session.flush()
                        first_user_id = first_user.id
                        second_user_id = second_user.id
                        first_address = Address(
                            user_id=first_user_id,
                            recipient_name="张三",
                            phone="13900139021",
                            province="浙江省",
                            city="杭州市",
                            district="西湖区",
                            detail="文三路 1 号",
                            is_default=True,
                        )
                        other_address = Address(
                            user_id=second_user_id,
                            recipient_name="李四",
                            phone="13900139022",
                            province="浙江省",
                            city="杭州市",
                            district="拱墅区",
                            detail="湖墅南路 2 号",
                            is_default=True,
                        )
                        dish = Dish(
                            category_id=category.id,
                            name="牛肉饭",
                            image_url="https://example.test/beef-rice.png",
                            price=Decimal("10.00"),
                            stock=5,
                            description="下单时的菜品描述",
                            is_available=True,
                        )
                        shop = await session.get(Shop, 1)
                        shop.is_open = False
                        shop.minimum_order_amount = Decimal("15.00")
                        shop.delivery_fee = Decimal("4.50")
                        session.add_all([first_address, other_address, dish])
                        await session.flush()
                        first_address_id = first_address.id
                        other_address_id = other_address.id
                        dish_id = dish.id
                        await session.commit()

                    first_headers = {
                        "Authorization": (
                            f"Bearer {create_access_token(str(first_user_id))}"
                        )
                    }
                    second_headers = {
                        "Authorization": (
                            f"Bearer {create_access_token(str(second_user_id))}"
                        )
                    }
                    admin_headers = {
                        "Authorization": (
                            f"Bearer {create_access_token('admin-1', token_type='admin')}"
                        )
                    }

                    await client.post(
                        "/api/cart/items",
                        json={"dish_id": dish_id, "quantity": 2},
                        headers=first_headers,
                    )

                    closed_order = await client.post(
                        "/api/orders",
                        json={"address_id": first_address_id},
                        headers=first_headers,
                    )
                    assert closed_order.status_code == 409
                    assert closed_order.json()["message"] == (
                        "店铺当前未营业，暂不可下单"
                    )

                    with_other_users_address = await client.post(
                        "/api/orders",
                        json={"address_id": other_address_id},
                        headers=first_headers,
                    )
                    assert with_other_users_address.status_code == 404
                    assert with_other_users_address.json()["message"] == (
                        "收货地址不存在"
                    )

                    async with session_factory() as session:
                        shop = await session.get(Shop, 1)
                        shop.is_open = True
                        shop.minimum_order_amount = Decimal("25.00")
                        await session.commit()

                    below_minimum = await client.post(
                        "/api/orders",
                        json={"address_id": first_address_id},
                        headers=first_headers,
                    )
                    assert below_minimum.status_code == 409
                    assert below_minimum.json()["message"] == (
                        "菜品金额未达到起送价"
                    )

                    async with session_factory() as session:
                        shop = await session.get(Shop, 1)
                        shop.minimum_order_amount = Decimal("15.00")
                        dish = await session.get(Dish, dish_id)
                        dish.stock = 1
                        await session.commit()

                    insufficient_stock = await client.post(
                        "/api/orders",
                        json={"address_id": first_address_id},
                        headers=first_headers,
                    )
                    assert insufficient_stock.status_code == 409
                    assert insufficient_stock.json()["message"] == (
                        "菜品“牛肉饭”库存不足"
                    )

                    async with session_factory() as session:
                        dish = await session.get(Dish, dish_id)
                        dish.stock = 5
                        dish.is_available = False
                        await session.commit()

                    unavailable_dish = await client.post(
                        "/api/orders",
                        json={"address_id": first_address_id},
                        headers=first_headers,
                    )
                    assert unavailable_dish.status_code == 409
                    assert unavailable_dish.json()["message"] == (
                        "购物车中存在已下架或已删除的菜品"
                    )

                    async with session_factory() as session:
                        dish = await session.get(Dish, dish_id)
                        dish.is_available = True
                        await session.commit()

                    unauthenticated = await client.post(
                        "/api/orders",
                        json={"address_id": first_address_id},
                    )
                    assert unauthenticated.status_code == 401

                    created_response = await client.post(
                        "/api/orders",
                        json={"address_id": first_address_id},
                        headers=first_headers,
                    )
                    assert created_response.status_code == 201
                    created_body = created_response.json()
                    assert created_body["code"] == 200
                    order = created_body["data"]
                    order_id = order["id"]
                    assert order["status"] == "pending_payment"
                    assert order["dish_amount"] == "20.00"
                    assert order["delivery_fee"] == "4.50"
                    assert order["total_amount"] == "24.50"
                    assert order["recipient_name"] == "张三"
                    assert order["items"][0]["dish_name"] == "牛肉饭"
                    assert order["items"][0]["category_name"] == "主食"
                    assert order["items"][0]["unit_price"] == "10.00"
                    assert order["items"][0]["quantity"] == 2

                    async with session_factory() as session:
                        dish = await session.get(Dish, dish_id)
                        assert dish.stock == 3
                        cart = await client.get("/api/cart", headers=first_headers)
                        assert cart.json()["data"]["total_quantity"] == 2
                        shop = await session.get(Shop, 1)
                        shop.delivery_fee = Decimal("9.00")
                        dish.name = "已改名菜品"
                        dish.price = Decimal("99.00")
                        address = await session.get(Address, first_address_id)
                        address.recipient_name = "新姓名"
                        address.detail = "新地址"
                        await session.commit()

                    own_order = await client.get(
                        f"/api/orders/{order_id}",
                        headers=first_headers,
                    )
                    snapshot = own_order.json()["data"]
                    assert snapshot["total_amount"] == "24.50"
                    assert snapshot["delivery_fee"] == "4.50"
                    assert snapshot["recipient_name"] == "张三"
                    assert snapshot["address_detail"] == "文三路 1 号"
                    assert snapshot["items"][0]["dish_name"] == "牛肉饭"
                    assert snapshot["items"][0]["unit_price"] == "10.00"

                    another_users_order = await client.get(
                        f"/api/orders/{order_id}",
                        headers=second_headers,
                    )
                    assert another_users_order.status_code == 404

                    cancelled = await client.post(
                        f"/api/orders/{order_id}/cancel",
                        headers=first_headers,
                    )
                    assert cancelled.status_code == 200
                    assert cancelled.json()["data"]["status"] == "cancelled"
                    async with session_factory() as session:
                        dish = await session.get(Dish, dish_id)
                        assert dish.stock == 5

                    cannot_cancel_twice = await client.post(
                        f"/api/orders/{order_id}/cancel",
                        headers=first_headers,
                    )
                    assert cannot_cancel_twice.status_code == 409

                    second_order_response = await client.post(
                        "/api/orders",
                        json={"address_id": first_address_id},
                        headers=first_headers,
                    )
                    assert second_order_response.status_code == 201
                    second_order_id = second_order_response.json()["data"]["id"]

                    forbidden_admin_list = await client.get("/api/admin/orders")
                    assert forbidden_admin_list.status_code == 401

                    admin_list = await client.get(
                        "/api/admin/orders",
                        headers=admin_headers,
                    )
                    assert admin_list.status_code == 200
                    assert len(admin_list.json()["data"]) == 2

                    first_transition = await client.patch(
                        f"/api/admin/orders/{second_order_id}/status",
                        json={"status": "pending_acceptance"},
                        headers=admin_headers,
                    )
                    assert first_transition.status_code == 200
                    assert first_transition.json()["data"]["status"] == (
                        "pending_acceptance"
                    )

                    user_cannot_cancel_paid = await client.post(
                        f"/api/orders/{second_order_id}/cancel",
                        headers=first_headers,
                    )
                    assert user_cannot_cancel_paid.status_code == 409

                    delivery_transition = await client.patch(
                        f"/api/admin/orders/{second_order_id}/status",
                        json={"status": "pending_delivery"},
                        headers=admin_headers,
                    )
                    assert delivery_transition.status_code == 200

                    complete_transition = await client.patch(
                        f"/api/admin/orders/{second_order_id}/status",
                        json={"status": "completed"},
                        headers=admin_headers,
                    )
                    assert complete_transition.status_code == 200
                    assert complete_transition.json()["data"]["status"] == "completed"

                    invalid_transition = await client.patch(
                        f"/api/admin/orders/{second_order_id}/status",
                        json={"status": "pending_delivery"},
                        headers=admin_headers,
                    )
                    assert invalid_transition.status_code == 409

                    user_orders = await client.get(
                        "/api/orders?page=1&page_size=1",
                        headers=first_headers,
                    )
                    assert len(user_orders.json()["data"]) == 1
                    filtered_admin_orders = await client.get(
                        "/api/admin/orders?status=completed",
                        headers=admin_headers,
                    )
                    assert len(filtered_admin_orders.json()["data"]) == 1

                    async with session_factory() as session:
                        additional_dish = Dish(
                            category_id=category.id,
                            name="小菜",
                            price=Decimal("3.00"),
                            stock=5,
                            is_available=True,
                        )
                        session.add(additional_dish)
                        await session.flush()
                        additional_dish_id = additional_dish.id
                        await session.commit()

                    await client.post(
                        "/api/cart/items",
                        json={"dish_id": additional_dish_id, "quantity": 1},
                        headers=first_headers,
                    )
                    multiple_items_order = await client.post(
                        "/api/orders",
                        json={"address_id": first_address_id},
                        headers=first_headers,
                    )
                    assert multiple_items_order.status_code == 201
                    assert [
                        item["category_name"]
                        for item in multiple_items_order.json()["data"]["items"]
                    ] == ["主食", "主食"]

                    async with session_factory() as session:
                        stored_order = await session.scalar(
                            select(Order).where(Order.id == second_order_id)
                        )
                        assert stored_order.status == "completed"
        finally:
            main_module.app.dependency_overrides.clear()
            await engine.dispose()

    asyncio.run(run_test())
