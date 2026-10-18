from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

StatisticsPeriod = Literal["today", "week", "month", "custom"]


class StatisticsTotals(BaseModel):
    order_count: int
    revenue: Decimal
    dish_revenue: Decimal
    delivery_revenue: Decimal
    dish_sales_quantity: int


class DishSalesRankingItem(BaseModel):
    dish_name: str
    category_name: str
    quantity: int
    sales_amount: Decimal


class StatisticsOverview(BaseModel):
    period: StatisticsPeriod
    start_date: date
    end_date: date
    all_time: StatisticsTotals
    selected_period: StatisticsTotals
    dish_sales_ranking: list[DishSalesRankingItem]
