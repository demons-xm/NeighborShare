import asyncio

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.database import get_db
from app.models.admin import Admin
from app.utils.token import create_access_token
import main as main_module


def test_public_shop_read_and_admin_update(monkeypatch):
    operations = main_module.app.openapi()["paths"]["/api/shop"]
    assert "security" not in operations["get"]
    assert operations["put"]["security"] == [{"HTTPBearer": []}]

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
                        session.add(
                            Admin(
                                username="admin-1",
                                password_hash="unused",
                            )
                        )
                        await session.commit()

                    public_response = await client.get("/api/shop")
                    assert public_response.status_code == 200
                    public_body = public_response.json()
                    assert public_body["code"] == 200
                    assert public_body["data"]["id"] == 1
                    assert public_body["data"]["is_open"] is False

                    unauthenticated = await client.put(
                        "/api/shop",
                        json={"shop_name": "新店名"},
                    )
                    assert unauthenticated.status_code == 401
                    assert unauthenticated.json()["message"] == "token invalid"

                    user_token = create_access_token("123")
                    user_response = await client.put(
                        "/api/shop",
                        json={"shop_name": "不应修改"},
                        headers={"Authorization": f"Bearer {user_token}"},
                    )
                    assert user_response.status_code == 401
                    assert user_response.json()["message"] == "no permission"

                    admin_token = create_access_token("1", token_type="admin")
                    admin_headers = {"Authorization": f"Bearer {admin_token}"}
                    update_response = await client.put(
                        "/api/shop",
                        json={
                            "shop_name": "测试餐厅",
                            "minimum_order_amount": "25.50",
                            "delivery_fee": "5.00",
                            "is_open": True,
                        },
                        headers=admin_headers,
                    )
                    assert update_response.status_code == 200
                    updated = update_response.json()["data"]
                    assert updated["shop_name"] == "测试餐厅"
                    assert updated["minimum_order_amount"] == "25.50"
                    assert updated["delivery_fee"] == "5.00"
                    assert updated["is_open"] is True

                    partial_response = await client.put(
                        "/api/shop",
                        json={"is_open": False},
                        headers=admin_headers,
                    )
                    partial = partial_response.json()["data"]
                    assert partial["is_open"] is False
                    assert partial["shop_name"] == "测试餐厅"
                    assert partial["delivery_fee"] == "5.00"

                    clear_logo_response = await client.put(
                        "/api/shop",
                        json={"logo_url": None},
                        headers=admin_headers,
                    )
                    assert clear_logo_response.status_code == 200
                    assert clear_logo_response.json()["data"]["logo_url"] is None

                    invalid_amount = await client.put(
                        "/api/shop",
                        json={"delivery_fee": "-1"},
                        headers=admin_headers,
                    )
                    assert invalid_amount.status_code == 422

                    empty_update = await client.put(
                        "/api/shop",
                        json={},
                        headers=admin_headers,
                    )
                    assert empty_update.status_code == 422
        finally:
            main_module.app.dependency_overrides.clear()
            await engine.dispose()

    asyncio.run(run_test())
