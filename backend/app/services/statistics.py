from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.order_item import OrderItem
from app.schemas.statistics import (
    DishSalesRankingItem,
    StatisticsOverview,
    StatisticsPeriod,
    StatisticsTotals,
)


def resolve_statistics_range(
    period: StatisticsPeriod,
    start_date: date | None = None,
    end_date: date | None = None,
    today: date | None = None,
) -> tuple[date, date]:
    if period == "custom":
        if start_date is None or end_date is None:
            raise ValueError("自定义时间段必须同时提供开始日期和结束日期")
        if start_date > end_date:
            raise ValueError("开始日期不能晚于结束日期")
        return start_date, end_date

    if start_date is not None or end_date is not None:
        raise ValueError("仅自定义时间段可以提供开始日期和结束日期")

    current_date = today or date.today()
    if period == "today":
        return current_date, current_date
    if period == "week":
        week_start = current_date - timedelta(days=current_date.weekday())
        return week_start, current_date

    month_start = current_date.replace(day=1)
    return month_start, current_date


def _datetime_range(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(start_date, time.min),
        datetime.combine(end_date + timedelta(days=1), time.min),
    )


async def _get_totals(
    session: AsyncSession,
    start_date: date | None = None,
    end_date: date | None = None,
) -> StatisticsTotals:
    order_query = select(
        func.count(Order.id),
        func.coalesce(func.sum(Order.total_amount), Decimal("0.00")),
        func.coalesce(func.sum(Order.dish_amount), Decimal("0.00")),
        func.coalesce(func.sum(Order.delivery_fee), Decimal("0.00")),
    ).where(Order.status == "completed")
    if start_date is not None and end_date is not None:
        range_start, range_end = _datetime_range(start_date, end_date)
        order_query = order_query.where(
            Order.create_time >= range_start,
            Order.create_time < range_end,
        )

    order_count, revenue, dish_revenue, delivery_revenue = (
        await session.execute(order_query)
    ).one()

    item_query = (
        select(func.coalesce(func.sum(OrderItem.quantity), 0))
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.status == "completed")
    )
    if start_date is not None and end_date is not None:
        item_query = item_query.where(
            Order.create_time >= range_start,
            Order.create_time < range_end,
        )
    dish_sales_quantity = await session.scalar(item_query)

    return StatisticsTotals(
        order_count=order_count,
        revenue=revenue,
        dish_revenue=dish_revenue,
        delivery_revenue=delivery_revenue,
        dish_sales_quantity=dish_sales_quantity or 0,
    )


async def get_statistics_overview(
    session: AsyncSession,
    period: StatisticsPeriod,
    start_date: date,
    end_date: date,
    top_n: int = 10,
) -> StatisticsOverview:
    all_time = await _get_totals(session)
    selected_period = await _get_totals(session, start_date, end_date)
    range_start, range_end = _datetime_range(start_date, end_date)
    ranking_rows = await session.execute(
        select(
            OrderItem.dish_name,
            OrderItem.category_name,
            func.sum(OrderItem.quantity).label("quantity"),
            func.sum(OrderItem.subtotal).label("sales_amount"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Order.status == "completed",
            Order.create_time >= range_start,
            Order.create_time < range_end,
        )
        .group_by(OrderItem.dish_name, OrderItem.category_name)
        .order_by(
            func.sum(OrderItem.quantity).desc(),
            func.sum(OrderItem.subtotal).desc(),
            OrderItem.dish_name.asc(),
        )
        .limit(top_n)
    )
    ranking = [
        DishSalesRankingItem(
            dish_name=row.dish_name,
            category_name=row.category_name,
            quantity=row.quantity,
            sales_amount=row.sales_amount,
        )
        for row in ranking_rows
    ]
    return StatisticsOverview(
        period=period,
        start_date=start_date,
        end_date=end_date,
        all_time=all_time,
        selected_period=selected_period,
        dish_sales_ranking=ranking,
    )
