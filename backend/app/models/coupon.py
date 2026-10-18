from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Coupon(Base):
    __tablename__ = "coupons"
    __table_args__ = (
        CheckConstraint("discount_amount > 0", name="ck_coupons_discount_positive"),
        CheckConstraint("minimum_order_amount >= 0", name="ck_coupons_minimum_nonnegative"),
        CheckConstraint("total_quantity > 0", name="ck_coupons_total_positive"),
        CheckConstraint("claimed_quantity >= 0", name="ck_coupons_claimed_nonnegative"),
        CheckConstraint(
            "claimed_quantity <= total_quantity",
            name="ck_coupons_claimed_within_total",
        ),
        CheckConstraint("per_user_limit > 0", name="ck_coupons_user_limit_positive"),
        CheckConstraint("end_time > start_time", name="ck_coupons_time_range"),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    minimum_order_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=0
    )
    total_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    claimed_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    per_user_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class UserCoupon(Base):
    __tablename__ = "user_coupons"
    __table_args__ = (
        CheckConstraint(
            "status IN ('available', 'used')",
            name="ck_user_coupons_status",
        ),
        Index("ix_user_coupons_user_coupon", "user_id", "coupon_id"),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    coupon_id: Mapped[int] = mapped_column(
        ForeignKey("coupons.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="available")
    claimed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    coupon: Mapped[Coupon] = relationship()
