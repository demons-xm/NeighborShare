import asyncio
from decimal import Decimal

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import config
from app.db.database import get_db
from app.models.order import Order
from app.models.user import User
from app.utils.token import create_access_token
import main as main_module


def test_payment_and_receipt_require_ownership_and_valid_status(monkeypatch):
    async def run_test():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        monkeypatch.setattr(main_module, "async_engine", engine)
        monkeypatch.setattr(config, "APP_ENV", "development")
        monkeypatch.setattr(config, "ENABLE_SIMULATED_PAYMENTS", True)
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
                    owner = User(
                        phone="13800138031",
                        password_hash="unused",
                    )
                    other_user = User(
                        phone="13800138032",
                        password_hash="unused",
                    )
                    session.add_all([owner, other_user])
                    await session.flush()

                    def make_order(user_id: int, status: str, order_no: str) -> Order:
                        return Order(
                            order_no=order_no,
                            user_id=user_id,
                            status=status,
                            recipient_name="消费者",
                            recipient_phone="13900139031",
                            province="浙江省",
                            city="杭州市",
                            district="西湖区",
                            address_detail="文三路 1 号",
                            dish_amount=Decimal("20.00"),
                            delivery_fee=Decimal("4.00"),
                            total_amount=Decimal("24.00"),
                        )

                    payment_order = make_order(
                        owner.id,
                        "pending_payment",
                        "payment-order-1",
                    )
                    foreign_order = make_order(
                        other_user.id,
                        "pending_payment",
                        "payment-order-2",
                    )
                    delivery_order = make_order(
                        owner.id,
                        "pending_delivery",
                        "payment-order-3",
                    )
                    session.add_all([payment_order, foreign_order, delivery_order])
                    await session.commit()
                    payment_order_id = payment_order.id
                    foreign_order_id = foreign_order.id
                    delivery_order_id = delivery_order.id

                headers = {
                    "Authorization": (
                        f"Bearer {create_access_token(str(owner.id))}"
                    )
                }
                async with AsyncClient(
                    transport=ASGITransport(app=main_module.app),
                    base_url="http://test",
                ) as client:
                    monkeypatch.setattr(config, "ENABLE_SIMULATED_PAYMENTS", False)
                    disabled_order = await client.post(
                        f"/api/orders/{payment_order_id}/pay",
                        headers=headers,
                    )
                    assert disabled_order.status_code == 503

                    monkeypatch.setattr(config, "APP_ENV", "production")
                    monkeypatch.setattr(config, "ENABLE_SIMULATED_PAYMENTS", True)
                    production_order = await client.post(
                        f"/api/orders/{payment_order_id}/pay",
                        headers=headers,
                    )
                    assert production_order.status_code == 503

                    monkeypatch.setattr(config, "APP_ENV", "development")
                    monkeypatch.setattr(config, "ENABLE_SIMULATED_PAYMENTS", True)
                    paid = await client.post(
                        f"/api/orders/{payment_order_id}/pay",
                        headers=headers,
                    )
                    assert paid.status_code == 200
                    assert paid.json()["data"]["status"] == "pending_acceptance"
                    assert paid.json()["message"] == "开发环境模拟支付成功"

                    repeated_payment = await client.post(
                        f"/api/orders/{payment_order_id}/pay",
                        headers=headers,
                    )
                    assert repeated_payment.status_code == 409

                    foreign_payment = await client.post(
                        f"/api/orders/{foreign_order_id}/pay",
                        headers=headers,
                    )
                    assert foreign_payment.status_code == 404

                    received = await client.post(
                        f"/api/orders/{delivery_order_id}/confirm-receipt",
                        headers=headers,
                    )
                    assert received.status_code == 200
                    assert received.json()["data"]["status"] == "completed"

                    repeated_receipt = await client.post(
                        f"/api/orders/{delivery_order_id}/confirm-receipt",
                        headers=headers,
                    )
                    assert repeated_receipt.status_code == 409

                    foreign_receipt = await client.post(
                        f"/api/orders/{foreign_order_id}/confirm-receipt",
                        headers=headers,
                    )
                    assert foreign_receipt.status_code == 404
        finally:
            main_module.app.dependency_overrides.clear()
            await engine.dispose()

    asyncio.run(run_test())
