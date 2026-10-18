import asyncio

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.database import get_db
from app.models import Address, User
from app.utils.token import create_access_token
import main as main_module


def test_address_crud_and_user_ownership(monkeypatch):
    address_paths = main_module.app.openapi()["paths"]
    for path in (
        "/api/address",
        "/api/address/{address_id}",
        "/api/address/{address_id}/default",
    ):
        for operation in address_paths[path].values():
            assert operation["security"] == [{"HTTPBearer": []}]

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
                        phone="13800138001",
                        password_hash="not-used-in-this-test",
                    )
                    second_user = User(
                        phone="13800138002",
                        password_hash="not-used-in-this-test",
                    )
                    async with session_factory() as session:
                        session.add_all([first_user, second_user])
                        await session.commit()
                        first_user_id = first_user.id
                        second_user_id = second_user.id

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

                    unauthenticated = await client.get("/api/address")
                    assert unauthenticated.status_code == 401
                    assert unauthenticated.json()["message"] == "token invalid"

                    first_payload = {
                        "recipient_name": "张三",
                        "phone": "13900139001",
                        "province": "浙江省",
                        "city": "杭州市",
                        "district": "西湖区",
                        "detail": "文三路 1 号",
                    }
                    first_created = await client.post(
                        "/api/address",
                        json=first_payload,
                        headers=first_headers,
                    )
                    assert first_created.status_code == 201
                    first_body = first_created.json()
                    assert first_body["code"] == 200
                    first_address_id = first_body["data"]["id"]
                    assert first_body["data"]["is_default"] is True

                    second_payload = {
                        **first_payload,
                        "recipient_name": "李四",
                        "detail": "文三路 2 号",
                    }
                    second_created = await client.post(
                        "/api/address",
                        json=second_payload,
                        headers=first_headers,
                    )
                    second_address_id = second_created.json()["data"]["id"]
                    assert second_created.json()["data"]["is_default"] is False

                    other_users_address = await client.post(
                        "/api/address",
                        json=first_payload,
                        headers=second_headers,
                    )
                    other_address_id = other_users_address.json()["data"]["id"]

                    listed = await client.get(
                        "/api/address",
                        headers=first_headers,
                    )
                    assert listed.status_code == 200
                    assert [item["id"] for item in listed.json()["data"]] == [
                        first_address_id,
                        second_address_id,
                    ]

                    forbidden_update = await client.put(
                        f"/api/address/{other_address_id}",
                        json={"detail": "越权修改"},
                        headers=first_headers,
                    )
                    assert forbidden_update.status_code == 404
                    assert forbidden_update.json()["message"] == "收货地址不存在"

                    forbidden_delete = await client.delete(
                        f"/api/address/{other_address_id}",
                        headers=first_headers,
                    )
                    assert forbidden_delete.status_code == 404

                    updated = await client.put(
                        f"/api/address/{second_address_id}",
                        json={"detail": "文三路 3 号"},
                        headers=first_headers,
                    )
                    assert updated.status_code == 200
                    assert updated.json()["data"]["detail"] == "文三路 3 号"

                    empty_update = await client.put(
                        f"/api/address/{second_address_id}",
                        json={},
                        headers=first_headers,
                    )
                    assert empty_update.status_code == 422

                    null_update = await client.put(
                        f"/api/address/{second_address_id}",
                        json={"detail": None},
                        headers=first_headers,
                    )
                    assert null_update.status_code == 422

                    default_response = await client.put(
                        f"/api/address/{second_address_id}/default",
                        headers=first_headers,
                    )
                    assert default_response.status_code == 200
                    assert default_response.json()["data"]["is_default"] is True

                    first_address = await client.get(
                        "/api/address",
                        headers=first_headers,
                    )
                    assert first_address.json()["data"][0]["id"] == second_address_id
                    assert sum(
                        item["is_default"] for item in first_address.json()["data"]
                    ) == 1

                    deleted = await client.delete(
                        f"/api/address/{second_address_id}",
                        headers=first_headers,
                    )
                    assert deleted.status_code == 200
                    remaining = await client.get(
                        "/api/address",
                        headers=first_headers,
                    )
                    assert len(remaining.json()["data"]) == 1
                    assert remaining.json()["data"][0]["is_default"] is True

                    async with session_factory() as session:
                        untouched_address = await session.get(Address, other_address_id)
                        assert untouched_address is not None
                        assert untouched_address.user_id == second_user_id
        finally:
            main_module.app.dependency_overrides.clear()
            await engine.dispose()

    asyncio.run(run_test())
