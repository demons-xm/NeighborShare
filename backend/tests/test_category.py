import asyncio

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.database import get_db
from app.models.admin import Admin
from app.utils.token import create_access_token
import main as main_module


def test_public_category_list_and_admin_crud(monkeypatch):
    operations = main_module.app.openapi()["paths"]["/api/categories"]
    assert "security" not in operations["get"]
    assert operations["post"]["security"] == [{"HTTPBearer": []}]
    assert main_module.app.openapi()["paths"]["/api/categories/{category_id}"][
        "put"
    ]["security"] == [{"HTTPBearer": []}]

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
                async with session_factory() as session:
                    session.add(Admin(username="admin-1", password_hash="unused"))
                    await session.commit()

                async with AsyncClient(
                    transport=ASGITransport(app=main_module.app),
                    base_url="http://test",
                ) as client:
                    headers = {
                        "Authorization": (
                            f"Bearer {create_access_token('admin-1', token_type='admin')}"
                        )
                    }
                    user_headers = {
                        "Authorization": f"Bearer {create_access_token('1')}"
                    }

                    public_empty = await client.get("/api/categories")
                    assert public_empty.status_code == 200
                    assert public_empty.json()["data"] == []

                    unauthenticated_create = await client.post(
                        "/api/categories",
                        json={"name": "招牌菜"},
                    )
                    assert unauthenticated_create.status_code == 401

                    forbidden_create = await client.post(
                        "/api/categories",
                        json={"name": "招牌菜"},
                        headers=user_headers,
                    )
                    assert forbidden_create.status_code == 401
                    assert forbidden_create.json()["message"] == "no permission"

                    featured = await client.post(
                        "/api/categories",
                        json={
                            "name": "招牌菜",
                            "description": "店铺特色",
                            "sort_order": 20,
                        },
                        headers=headers,
                    )
                    assert featured.status_code == 201
                    featured_id = featured.json()["data"]["id"]

                    drinks = await client.post(
                        "/api/categories",
                        json={"name": "饮品", "sort_order": 10},
                        headers=headers,
                    )
                    drinks_id = drinks.json()["data"]["id"]

                    main_dishes = await client.post(
                        "/api/categories",
                        json={"name": "主食", "sort_order": 20},
                        headers=headers,
                    )
                    main_dishes_id = main_dishes.json()["data"]["id"]

                    public_list = await client.get("/api/categories")
                    assert [
                        item["id"] for item in public_list.json()["data"]
                    ] == [drinks_id, featured_id, main_dishes_id]

                    updated = await client.put(
                        f"/api/categories/{featured_id}",
                        json={"name": "人气招牌", "sort_order": 5},
                        headers=headers,
                    )
                    assert updated.status_code == 200
                    assert updated.json()["data"]["name"] == "人气招牌"
                    assert updated.json()["data"]["description"] == "店铺特色"

                    empty_update = await client.put(
                        f"/api/categories/{featured_id}",
                        json={},
                        headers=headers,
                    )
                    assert empty_update.status_code == 422

                    null_name_update = await client.put(
                        f"/api/categories/{featured_id}",
                        json={"name": None},
                        headers=headers,
                    )
                    assert null_name_update.status_code == 422

                    reordered = await client.get("/api/categories")
                    assert reordered.json()["data"][0]["id"] == featured_id

                    deleted = await client.delete(
                        f"/api/categories/{drinks_id}",
                        headers=headers,
                    )
                    assert deleted.status_code == 200
                    assert deleted.json()["message"] == "分类删除成功"

                    not_found = await client.delete(
                        f"/api/categories/{drinks_id}",
                        headers=headers,
                    )
                    assert not_found.status_code == 404
                    assert not_found.json()["message"] == "分类不存在"
        finally:
            main_module.app.dependency_overrides.clear()
            await engine.dispose()

    asyncio.run(run_test())
