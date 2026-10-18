import asyncio
from datetime import timedelta

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.database import get_db
from app.models import User
from app.routers import auth as auth_router_module
from app.utils.password import verify_password
from app.utils.token import create_access_token
import main as main_module


def test_registration_endpoint(monkeypatch):
    openapi = main_module.app.openapi()
    me_operation = openapi["paths"]["/api/v1/auth/me"]["get"]
    assert "401" in me_operation["responses"]
    assert me_operation["responses"]["401"]["content"]["application/json"]["schema"]
    assert me_operation["security"] == [{"HTTPBearer": []}]

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
                    response = await client.post(
                        "/api/v1/auth/register",
                        json={"phone": "13800138000", "password": "secure-pass-123"},
                    )
                    assert response.status_code == 201
                    success_body = response.json()
                    assert success_body["code"] == 200
                    assert success_body["message"] == "注册成功"
                    assert success_body["data"]["phone"] == "13800138000"
                    assert "password" not in success_body["data"]
                    assert "password_hash" not in success_body["data"]

                    async with session_factory() as session:
                        user = await session.get(User, success_body["data"]["id"])
                        assert user is not None
                        assert user.password_hash != "secure-pass-123"
                        assert verify_password("secure-pass-123", user.password_hash)

                        login_response = await client.post(
                            "/api/v1/auth/login",
                            json={"phone": "13800138000", "password": "secure-pass-123"},
                        )
                        assert login_response.status_code == 200
                        login_body = login_response.json()
                        assert login_body["code"] == 200
                        assert login_body["message"] == "登录成功"
                        assert login_body["data"]["token_type"] == "Bearer"
                        assert login_body["data"]["expires_in"] == 7200
                        token = login_body["data"]["access_token"]

                        invalid_token_response = await client.get(
                            "/api/v1/auth/me",
                            headers={"Authorization": "Bearer not-a-jwt"},
                        )
                        assert invalid_token_response.status_code == 401
                        assert invalid_token_response.json()["message"] == "token invalid"

                        me_response = await client.get(
                            "/api/v1/auth/me",
                            headers={"Authorization": f"Bearer {token}"},
                        )
                        assert me_response.status_code == 200
                        assert me_response.json()["data"]["phone"] == "13800138000"

                        unauthenticated_response = await client.get("/api/v1/auth/me")
                        assert unauthenticated_response.status_code == 401
                        assert unauthenticated_response.json() == {
                            "code": 401,
                            "message": "token invalid",
                            "data": None,
                        }

                        expired_token = create_access_token(
                            subject=str(user.id),
                            expires_delta=timedelta(seconds=-1),
                        )
                        expired_response = await client.get(
                            "/api/v1/auth/me",
                            headers={"Authorization": f"Bearer {expired_token}"},
                        )
                        assert expired_response.status_code == 401
                        assert expired_response.json()["message"] == "token expired"

                        admin_token = create_access_token(
                            subject=str(user.id),
                            token_type="admin",
                        )
                        permission_response = await client.get(
                            "/api/v1/auth/me",
                            headers={"Authorization": f"Bearer {admin_token}"},
                        )
                        assert permission_response.status_code == 401
                        assert permission_response.json()["message"] == "no permission"

                        invalid_login_response = await client.post(
                            "/api/v1/auth/login",
                            json={"phone": "13800138000", "password": "wrong-pass"},
                        )
                        assert invalid_login_response.status_code == 401
                        assert invalid_login_response.json()["code"] == 401

                    duplicate_response = await client.post(
                        "/api/v1/auth/register",
                        json={"phone": "13800138000", "password": "secure-pass-123"},
                    )
                    assert duplicate_response.status_code == 409
                    assert duplicate_response.json() == {
                        "code": 409,
                        "message": "该手机号已注册",
                        "data": None,
                    }

                    invalid_phone_response = await client.post(
                        "/api/v1/auth/register",
                        json={"phone": "123", "password": "secure-pass-123"},
                    )
                    assert invalid_phone_response.status_code == 422
                    assert invalid_phone_response.json() == {
                        "code": 422,
                        "message": "请求参数校验失败",
                        "data": None,
                    }

                    invalid_password_response = await client.post(
                        "/api/v1/auth/register",
                        json={"phone": "13900139000", "password": "short"},
                    )
                    assert invalid_password_response.status_code == 422
                    assert invalid_password_response.json() == {
                        "code": 422,
                        "message": "请求参数校验失败",
                        "data": None,
                    }

                    oversized_password_response = await client.post(
                        "/api/v1/auth/register",
                        json={"phone": "13900139000", "password": "密码" * 25},
                    )
                    assert oversized_password_response.status_code == 422
                    assert oversized_password_response.json()["code"] == 422

                    not_found_response = await client.get("/not-found")
                    assert not_found_response.status_code == 404
                    assert not_found_response.json() == {
                        "code": 404,
                        "message": "Not Found",
                        "data": None,
                    }

                    async def fail_registration(session, user_data):
                        raise RuntimeError("test failure")

                    monkeypatch.setattr(
                        auth_router_module,
                        "register_user",
                        fail_registration,
                    )
                    async with AsyncClient(
                        transport=ASGITransport(
                            app=main_module.app,
                            raise_app_exceptions=False,
                        ),
                        base_url="http://test",
                    ) as error_client:
                        server_error_response = await error_client.post(
                            "/api/v1/auth/register",
                            json={
                                "phone": "13900139000",
                                "password": "secure-pass-123",
                            },
                        )
                    assert server_error_response.status_code == 500
                    assert server_error_response.json() == {
                        "code": 500,
                        "message": "服务器内部错误",
                        "data": None,
                    }
        finally:
            main_module.app.dependency_overrides.clear()
            await engine.dispose()

    asyncio.run(run_test())
