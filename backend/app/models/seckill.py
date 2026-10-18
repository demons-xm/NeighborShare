from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.dish import Dish


class SeckillActivity(Base):
    __tablename__ = "seckill_activities"
    __table_args__ = (
        CheckConstraint("sale_price >= 0", name="ck_seckill_sale_price_nonnegative"),
        CheckConstraint("stock > 0", name="ck_seckill_stock_positive"),
        CheckConstraint("sold_count >= 0", name="ck_seckill_sold_nonnegative"),
        CheckConstraint("sold_count <= stock", name="ck_seckill_sold_within_stock"),
        CheckConstraint("limit_per_user > 0", name="ck_seckill_user_limit_positive"),
        CheckConstraint("end_time > start_time", name="ck_seckill_time_range"),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    dish_id: Mapped[int] = mapped_column(
        ForeignKey("dishes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sale_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False)
    sold_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    limit_per_user: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    dish: Mapped["Dish"] = relationship()
