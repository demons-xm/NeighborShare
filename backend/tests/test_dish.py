import asyncio

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.database import get_db
from app.models.admin import Admin
from app.models.category import Category
from app.services.dish import (
    DishUnavailableError,
    InsufficientStockError,
    validate_dish_for_order,
)
from app.utils.token import create_access_token
import main as main_module


def test_public_dish_listing_and_admin_management(monkeypatch):
    openapi = main_module.app.openapi()
    assert "security" not in openapi["paths"]["/api/dishes"]["get"]
    assert "security" not in openapi["paths"]["/api/dishes/{dish_id}"]["get"]
    assert openapi["paths"]["/api/admin/dishes"]["post"]["security"] == [
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
                    async with session_factory() as session:
                        session.add(Admin(username="admin-1", password_hash="unused"))
                        category = Category(
                            shop_id=1,
                            name="招牌菜",
                            sort_order=10,
                        )
                        session.add(category)
                        await session.commit()
                        category_id = category.id

                    admin_headers = {
                        "Authorization": (
                            f"Bearer {create_access_token('admin-1', token_type='admin')}"
                        )
                    }
                    user_headers = {
                        "Authorization": f"Bearer {create_access_token('1')}"
                    }

                    unauthenticated_admin_query = await client.get(
                        "/api/admin/dishes"
                    )
                    assert unauthenticated_admin_query.status_code == 401

                    forbidden_create = await client.post(
                        "/api/admin/dishes",
                        json={
                            "name": "牛肉饭",
                            "price": "18.50",
                            "stock": 10,
                            "category_id": category_id,
                        },
                        headers=user_headers,
                    )
                    assert forbidden_create.status_code == 401
                    assert forbidden_create.json()["message"] == "no permission"

                    create_response = await client.post(
                        "/api/admin/dishes",
                        json={
                            "name": "牛肉饭",
                            "image_url": "https://example.test/beef-rice.png",
                            "price": "18.50",
                            "stock": 10,
                            "description": "招牌牛肉饭",
                            "category_id": category_id,
                        },
                        headers=admin_headers,
                    )
                    assert create_response.status_code == 201
                    created = create_response.json()["data"]
                    assert created["price"] == "18.50"
                    assert created["category"]["name"] == "招牌菜"
                    dish_id = created["id"]

                    invalid_category = await client.post(
                        "/api/admin/dishes",
                        json={
                            "name": "孤儿菜品",
                            "price": "1.00",
                            "category_id": 9999,
                        },
                        headers=admin_headers,
                    )
                    assert invalid_category.status_code == 404
                    assert invalid_category.json()["message"] == "菜品分类不存在"

                    public_list = await client.get("/api/dishes")
                    assert public_list.status_code == 200
                    assert [item["id"] for item in public_list.json()["data"]] == [
                        dish_id
                    ]
                    assert public_list.json()["data"][0]["category_id"] == category_id

                    public_detail = await client.get(f"/api/dishes/{dish_id}")
                    assert public_detail.status_code == 200
                    assert public_detail.json()["data"]["name"] == "牛肉饭"

                    updated = await client.put(
                        f"/api/admin/dishes/{dish_id}",
                        json={"price": "20.00", "stock": 5},
                        headers=admin_headers,
                    )
                    assert updated.status_code == 200
                    assert updated.json()["data"]["price"] == "20.00"
                    assert updated.json()["data"]["stock"] == 5

                    empty_update = await client.put(
                        f"/api/admin/dishes/{dish_id}",
                        json={},
                        headers=admin_headers,
                    )
                    assert empty_update.status_code == 422

                    invalid_price = await client.put(
                        f"/api/admin/dishes/{dish_id}",
                        json={"price": "-1"},
                        headers=admin_headers,
                    )
                    assert invalid_price.status_code == 422

                    deleted_category = await client.delete(
                        f"/api/categories/{category_id}",
                        headers=admin_headers,
                    )
                    assert deleted_category.status_code == 409
                    assert deleted_category.json()["message"] == (
                        "分类下仍有菜品，不能删除"
                    )

                    async with session_factory() as session:
                        valid_dish = await validate_dish_for_order(
                            session,
                            dish_id,
                            quantity=5,
                        )
                        assert valid_dish.id == dish_id
                        try:
                            await validate_dish_for_order(
                                session,
                                dish_id,
                                quantity=6,
                            )
                        except InsufficientStockError:
                            pass
                        else:
                            raise AssertionError("Expected insufficient stock error")

                    hide_response = await client.patch(
                        f"/api/admin/dishes/{dish_id}/availability",
                        json={"is_available": False},
                        headers=admin_headers,
                    )
                    assert hide_response.status_code == 200
                    assert hide_response.json()["data"]["is_available"] is False

                    assert (await client.get("/api/dishes")).json()["data"] == []
                    assert (
                        await client.get(f"/api/dishes/{dish_id}")
                    ).status_code == 404

                    admin_list = await client.get(
                        "/api/admin/dishes",
                        headers=admin_headers,
                    )
                    assert len(admin_list.json()["data"]) == 1
                    assert admin_list.json()["data"][0]["is_available"] is False

                    async with session_factory() as session:
                        try:
                            await validate_dish_for_order(session, dish_id, quantity=1)
                        except DishUnavailableError:
                            pass
                        else:
                            raise AssertionError("Expected unavailable dish error")

                    delete_response = await client.delete(
                        f"/api/admin/dishes/{dish_id}",
                        headers=admin_headers,
                    )
                    assert delete_response.status_code == 200
                    assert (await client.get("/api/admin/dishes", headers=admin_headers)).json()["data"] == []
        finally:
            main_module.app.dependency_overrides.clear()
            await engine.dispose()

    asyncio.run(run_test())
