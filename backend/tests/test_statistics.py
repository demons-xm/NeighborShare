import asyncio
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.database import get_db
from app.models.admin import Admin
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.user import User
from app.services.statistics import resolve_statistics_range
from app.utils.token import create_access_token
import main as main_module


def test_statistics_only_count_completed_orders(monkeypatch):
    overview_operation = main_module.app.openapi()["paths"][
        "/api/admin/statistics/overview"
    ]["get"]
    assert overview_operation["security"] == [{"HTTPBearer": []}]

    assert resolve_statistics_range("today", today=date(2026, 10, 10)) == (
        date(2026, 10, 10),
        date(2026, 10, 10),
    )
    assert resolve_statistics_range("week", today=date(2026, 10, 10)) == (
        date(2026, 10, 5),
        date(2026, 10, 10),
    )
    assert resolve_statistics_range("month", today=date(2026, 10, 10)) == (
        date(2026, 10, 1),
        date(2026, 10, 10),
    )

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
                    today = date.today()
                    yesterday = today - timedelta(days=1)
                    admin = Admin(username="stats-admin", password_hash="unused")
                    user = User(phone="13800138030", password_hash="unused")
                    async with session_factory() as session:
                        session.add_all([admin, user])
                        await session.flush()
                        admin_id = admin.id
                        user_id = user.id

                        def add_order(
                            order_no: str,
                            status: str,
                            created_on: date,
                            dish_amount: str,
                            delivery_fee: str,
                            total_amount: str,
                            dish_name: str,
                            category_name: str,
                            quantity: int,
                        ) -> None:
                            order = Order(
                                order_no=order_no,
                                user_id=user_id,
                                status=status,
                                recipient_name="统计测试",
                                recipient_phone="13900139030",
                                province="浙江省",
                                city="杭州市",
                                district="西湖区",
                                address_detail="测试路 1 号",
                                dish_amount=Decimal(dish_amount),
                                delivery_fee=Decimal(delivery_fee),
                                total_amount=Decimal(total_amount),
                                create_time=datetime.combine(
                                    created_on,
                                    time(hour=12),
                                ),
                            )
                            order.items.append(
                                OrderItem(
                                    dish_name=dish_name,
                                    category_name=category_name,
                                    unit_price=Decimal(dish_amount) / quantity,
                                    quantity=quantity,
                                    subtotal=Decimal(dish_amount),
                                )
                            )
                            session.add(order)

                        add_order(
                            "completed-today-1",
                            "completed",
                            today,
                            "20.00",
                            "4.50",
                            "24.50",
                            "牛肉饭",
                            "主食",
                            2,
                        )
                        add_order(
                            "completed-today-2",
                            "completed",
                            today,
                            "6.00",
                            "2.00",
                            "8.00",
                            "柠檬茶",
                            "饮品",
                            3,
                        )
                        add_order(
                            "cancelled-today",
                            "cancelled",
                            today,
                            "100.00",
                            "0.00",
                            "100.00",
                            "取消菜品",
                            "主食",
                            99,
                        )
                        add_order(
                            "pending-today",
                            "pending_payment",
                            today,
                            "50.00",
                            "0.00",
                            "50.00",
                            "未完成菜品",
                            "主食",
                            10,
                        )
                        add_order(
                            "completed-yesterday",
                            "completed",
                            yesterday,
                            "10.00",
                            "2.00",
                            "12.00",
                            "牛肉饭",
                            "主食",
                            1,
                        )
                        await session.commit()

                    admin_headers = {
                        "Authorization": (
                            "Bearer "
                            + create_access_token(
                                str(admin_id),
                                token_type="admin",
                            )
                        )
                    }
                    unauthorized = await client.get(
                        "/api/admin/statistics/overview"
                    )
                    assert unauthorized.status_code == 401

                    user_token = create_access_token(str(user_id))
                    forbidden = await client.get(
                        "/api/admin/statistics/overview",
                        headers={"Authorization": f"Bearer {user_token}"},
                    )
                    assert forbidden.status_code == 401
                    assert forbidden.json()["message"] == "no permission"

                    response = await client.get(
                        "/api/admin/statistics/overview",
                        params={
                            "period": "custom",
                            "start_date": today.isoformat(),
                            "end_date": today.isoformat(),
                            "top_n": 1,
                        },
                        headers=admin_headers,
                    )
                    assert response.status_code == 200
                    data = response.json()["data"]
                    assert data["selected_period"] == {
                        "order_count": 2,
                        "revenue": "32.50",
                        "dish_revenue": "26.00",
                        "delivery_revenue": "6.50",
                        "dish_sales_quantity": 5,
                    }
                    assert data["all_time"] == {
                        "order_count": 3,
                        "revenue": "44.50",
                        "dish_revenue": "36.00",
                        "delivery_revenue": "8.50",
                        "dish_sales_quantity": 6,
                    }
                    assert data["dish_sales_ranking"] == [
                        {
                            "dish_name": "柠檬茶",
                            "category_name": "饮品",
                            "quantity": 3,
                            "sales_amount": "6.00",
                        }
                    ]

                    invalid_range = await client.get(
                        "/api/admin/statistics/overview",
                        params={"period": "custom", "start_date": today.isoformat()},
                        headers=admin_headers,
                    )
                    assert invalid_range.status_code == 422
                    assert invalid_range.json()["code"] == 422

                    non_custom_dates = await client.get(
                        "/api/admin/statistics/overview",
                        params={
                            "period": "today",
                            "start_date": today.isoformat(),
                            "end_date": today.isoformat(),
                        },
                        headers=admin_headers,
                    )
                    assert non_custom_dates.status_code == 422
        finally:
            main_module.app.dependency_overrides.clear()
            await engine.dispose()

    asyncio.run(run_test())
