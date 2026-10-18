import asyncio

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.database import get_db
from app.models.admin import Admin
from app.models.category import Category
from app.models.dish import Dish
from app.models.user import User
from app.utils.token import create_access_token
import main as main_module


def test_user_cart_crud_and_dish_availability(monkeypatch):
    openapi = main_module.app.openapi()
    for path, methods in {
        "/api/cart": ("get",),
        "/api/cart/items": ("post", "delete"),
        "/api/cart/items/{dish_id}": ("put", "delete"),
    }.items():
        for method in methods:
            assert openapi["paths"][path][method]["security"] == [
                {"HTTPBearer": []}
            ]

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
                    first_user = User(
                        phone="13800138011",
                        password_hash="unused",
                    )
                    second_user = User(
                        phone="13800138012",
                        password_hash="unused",
                    )
                    admin = Admin(username="admin-1", password_hash="unused")
                    category = Category(shop_id=1, name="主食")
                    async with session_factory() as session:
                        session.add_all([first_user, second_user, admin, category])
                        await session.flush()
                        first_user_id = first_user.id
                        second_user_id = second_user.id
                        first_dish = Dish(
                            category_id=category.id,
                            name="牛肉饭",
                            price="18.50",
                            stock=4,
                            is_available=True,
                        )
                        second_dish = Dish(
                            category_id=category.id,
                            name="饮料",
                            price="5.00",
                            stock=20,
                            is_available=True,
                        )
                        session.add_all([first_dish, second_dish])
                        await session.flush()
                        first_dish_id = first_dish.id
                        second_dish_id = second_dish.id
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

                    unauthorized = await client.get("/api/cart")
                    assert unauthorized.status_code == 401
                    assert unauthorized.json()["message"] == "token invalid"

                    empty_cart = await client.get(
                        "/api/cart",
                        headers=first_headers,
                    )
                    assert empty_cart.status_code == 200
                    assert empty_cart.json()["data"] == {
                        "items": [],
                        "total_quantity": 0,
                        "total_amount": "0.00",
                    }

                    added = await client.post(
                        "/api/cart/items",
                        json={"dish_id": first_dish_id, "quantity": 2},
                        headers=first_headers,
                    )
                    assert added.status_code == 201
                    assert added.json()["data"]["total_quantity"] == 2
                    assert added.json()["data"]["total_amount"] == "37.00"

                    incremented = await client.post(
                        "/api/cart/items",
                        json={"dish_id": first_dish_id, "quantity": 1},
                        headers=first_headers,
                    )
                    assert incremented.json()["data"]["items"][0]["quantity"] == 3

                    second_user_cart = await client.post(
                        "/api/cart/items",
                        json={"dish_id": first_dish_id, "quantity": 1},
                        headers=second_headers,
                    )
                    assert second_user_cart.status_code == 201
                    assert second_user_cart.json()["data"]["total_quantity"] == 1

                    update_quantity = await client.put(
                        f"/api/cart/items/{first_dish_id}",
                        json={"quantity": 2},
                        headers=first_headers,
                    )
                    assert update_quantity.status_code == 200
                    assert update_quantity.json()["data"]["total_quantity"] == 2

                    not_in_cart = await client.delete(
                        f"/api/cart/items/{second_dish_id}",
                        headers=first_headers,
                    )
                    assert not_in_cart.status_code == 404

                    invalid_quantity = await client.put(
                        f"/api/cart/items/{first_dish_id}",
                        json={"quantity": 0},
                        headers=first_headers,
                    )
                    assert invalid_quantity.status_code == 422

                    missing_cart_item = await client.put(
                        f"/api/cart/items/{second_dish_id}",
                        json={"quantity": 2},
                        headers=second_headers,
                    )
                    assert missing_cart_item.status_code == 404

                    async with session_factory() as session:
                        dish = await session.get(Dish, first_dish_id)
                        assert dish is not None
                        dish.is_available = False
                        await session.commit()

                    retained = await client.get("/api/cart", headers=first_headers)
                    retained_item = retained.json()["data"]["items"][0]
                    assert retained_item["dish_id"] == first_dish_id
                    assert retained_item["dish"]["is_available"] is False

                    cannot_add_unavailable = await client.post(
                        "/api/cart/items",
                        json={"dish_id": first_dish_id, "quantity": 1},
                        headers=first_headers,
                    )
                    assert cannot_add_unavailable.status_code == 409

                    remove_item = await client.delete(
                        f"/api/cart/items/{first_dish_id}",
                        headers=first_headers,
                    )
                    assert remove_item.status_code == 200
                    assert remove_item.json()["data"]["items"] == []

                    await client.post(
                        "/api/cart/items",
                        json={"dish_id": second_dish_id, "quantity": 2},
                        headers=first_headers,
                    )
                    cleared = await client.delete(
                        "/api/cart/items",
                        headers=first_headers,
                    )
                    assert cleared.status_code == 200
                    assert cleared.json()["data"]["items"] == []
                    assert cleared.json()["data"]["total_quantity"] == 0

                    other_cart = await client.get(
                        "/api/cart",
                        headers=second_headers,
                    )
                    assert other_cart.json()["data"]["total_quantity"] == 1

                    admin_headers = {
                        "Authorization": (
                            f"Bearer {create_access_token('admin-1', token_type='admin')}"
                        )
                    }
                    delete_dish = await client.delete(
                        f"/api/admin/dishes/{first_dish_id}",
                        headers=admin_headers,
                    )
                    assert delete_dish.status_code == 200
                    cart_after_dish_delete = await client.get(
                        "/api/cart",
                        headers=second_headers,
                    )
                    assert cart_after_dish_delete.json()["data"]["items"] == []
        finally:
            main_module.app.dependency_overrides.clear()
            await engine.dispose()

    asyncio.run(run_test())
