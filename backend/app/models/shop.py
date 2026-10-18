from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Shop(Base):
    __tablename__ = "shop"
    __table_args__ = (CheckConstraint("id = 1", name="ck_shop_singleton"),)

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    shop_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="邻享店铺",
    )
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    business_hours: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="09:00-21:00",
    )
    delivery_range: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
    )
    minimum_order_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    delivery_fee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    is_open: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
