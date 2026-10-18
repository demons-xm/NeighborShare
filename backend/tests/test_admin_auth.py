import asyncio

import jwt
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import config
from app.db.database import get_db
from app.models.admin import Admin
from app.models.user import User
from app.utils.password import hash_password
import main as main_module


def test_independent_admin_login_and_backend_authorization(monkeypatch):
    monkeypatch.setattr(config, "ADMIN_USERNAME", "shop-manager")
    monkeypatch.setattr(config, "ADMIN_PASSWORD", "manager-password-123")

    openapi = main_module.app.openapi()
    assert "/api/admin/auth/login" in openapi["paths"]
    assert openapi["paths"]["/api/admin/orders"]["get"]["security"] == [
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
                        admin = await session.scalar(
                            select(Admin).where(Admin.username == "shop-manager")
                        )
                        assert admin is not None
                        assert admin.password_hash != "manager-password-123"
                        session.add(
                            User(
                                phone="13800138020",
                                password_hash=hash_password("user-password-123"),
                            )
                        )
                        await session.commit()

                    register = await client.post(
                        "/api/admin/auth/register",
                        json={
                            "username": "new-merchant",
                            "password": "new-merchant-password",
                        },
                    )
                    assert register.status_code == 201
                    assert register.json()["code"] == 200
                    assert register.json()["message"] == "商家注册成功，请登录"
                    assert register.json()["data"]["username"] == "new-merchant"
                    assert "password" not in register.json()["data"]
                    assert "password_hash" not in register.json()["data"]

                    async with session_factory() as session:
                        registered_admin = await session.scalar(
                            select(Admin).where(Admin.username == "new-merchant")
                        )
                        assert registered_admin.password_hash != (
                            "new-merchant-password"
                        )

                    duplicate_registration = await client.post(
                        "/api/admin/auth/register",
                        json={
                            "username": "new-merchant",
                            "password": "different-password",
                        },
                    )
                    assert duplicate_registration.status_code == 409
                    assert duplicate_registration.json()["message"] == (
                        "管理员用户名已注册"
                    )

                    short_password = await client.post(
                        "/api/admin/auth/register",
                        json={"username": "another-admin", "password": "short"},
                    )
                    assert short_password.status_code == 422

                    registered_login = await client.post(
                        "/api/admin/auth/login",
                        json={
                            "username": "new-merchant",
                            "password": "new-merchant-password",
                        },
                    )
                    assert registered_login.status_code == 200

                    wrong_password = await client.post(
                        "/api/admin/auth/login",
                        json={
                            "username": "shop-manager",
                            "password": "incorrect-password",
                        },
                    )
                    assert wrong_password.status_code == 401
                    assert wrong_password.json() == {
                        "code": 401,
                        "message": "管理员账号或密码错误",
                        "data": None,
                    }

                    user_as_admin = await client.post(
                        "/api/admin/auth/login",
                        json={
                            "username": "13800138020",
                            "password": "user-password-123",
                        },
                    )
                    assert user_as_admin.status_code == 401

                    login = await client.post(
                        "/api/admin/auth/login",
                        json={
                            "username": "shop-manager",
                            "password": "manager-password-123",
                        },
                    )
                    assert login.status_code == 200
                    login_data = login.json()["data"]
                    assert login_data["token_type"] == "Bearer"
                    assert login_data["expires_in"] == 7200
                    assert login_data["admin"]["username"] == "shop-manager"
                    assert "password_hash" not in login_data["admin"]
                    payload = jwt.decode(
                        login_data["access_token"],
                        config.JWT_SECRET_KEY,
                        algorithms=["HS256"],
                    )
                    assert payload["type"] == "admin"
                    assert payload["sub"] == str(login_data["admin"]["id"])
                    assert "exp" in payload

                    admin_headers = {
                        "Authorization": f"Bearer {login_data['access_token']}"
                    }
                    admin_orders = await client.get(
                        "/api/admin/orders",
                        headers=admin_headers,
                    )
                    assert admin_orders.status_code == 200

                    user_login = await client.post(
                        "/api/v1/auth/login",
                        json={
                            "phone": "13800138020",
                            "password": "user-password-123",
                        },
                    )
                    user_headers = {
                        "Authorization": (
                            f"Bearer {user_login.json()['data']['access_token']}"
                        )
                    }
                    forbidden = await client.get(
                        "/api/admin/orders",
                        headers=user_headers,
                    )
                    assert forbidden.status_code == 401
                    assert forbidden.json()["message"] == "no permission"

                    admin_on_user_route = await client.get(
                        "/api/v1/auth/me",
                        headers=admin_headers,
                    )
                    assert admin_on_user_route.status_code == 401
                    assert admin_on_user_route.json()["message"] == "no permission"

                    async with session_factory() as session:
                        admin = await session.scalar(
                            select(Admin).where(Admin.username == "shop-manager")
                        )
                        admin.is_active = False
                        await session.commit()

                    disabled_admin = await client.get(
                        "/api/admin/orders",
                        headers=admin_headers,
                    )
                    assert disabled_admin.status_code == 401
                    assert disabled_admin.json()["message"] == "token invalid"
        finally:
            main_module.app.dependency_overrides.clear()
            await engine.dispose()

    asyncio.run(run_test())
