from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


class CouponCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    discount_amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    minimum_order_amount: Decimal = Field(default=0, ge=0, max_digits=10, decimal_places=2)
    total_quantity: int = Field(gt=0, le=1_000_000)
    per_user_limit: int = Field(default=1, ge=1, le=100)
    start_time: datetime
    end_time: datetime
    is_active: bool = True

    @field_validator("start_time", "end_time")
    @classmethod
    def use_utc(cls, value: datetime) -> datetime:
        return normalize_utc(value)

    @model_validator(mode="after")
    def validate_time_range(self) -> "CouponCreate":
        if self.end_time <= self.start_time:
            raise ValueError("优惠券结束时间必须晚于开始时间")
        return self


class CouponUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    discount_amount: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    minimum_order_amount: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    total_quantity: int | None = Field(default=None, gt=0, le=1_000_000)
    per_user_limit: int | None = Field(default=None, ge=1, le=100)
    start_time: datetime | None = None
    end_time: datetime | None = None
    is_active: bool | None = None

    @field_validator("start_time", "end_time")
    @classmethod
    def use_utc(cls, value: datetime | None) -> datetime | None:
        return normalize_utc(value) if value is not None else None

    @model_validator(mode="after")
    def validate_update(self) -> "CouponUpdate":
        if not self.model_fields_set:
            raise ValueError("至少提供一个需要更新的字段")
        if any(
            getattr(self, field) is None
            for field in self.model_fields_set
            if field != "description"
        ):
            raise ValueError("更新字段不能为 null")
        return self


class CouponActiveUpdate(BaseModel):
    is_active: bool


class CouponPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    discount_amount: Decimal
    minimum_order_amount: Decimal
    total_quantity: int
    claimed_quantity: int
    per_user_limit: int
    start_time: datetime
    end_time: datetime
    is_active: bool


class UserCouponPublic(BaseModel):
    id: int
    status: str
    claimed_at: datetime
    redeemed_at: datetime | None
    coupon: CouponPublic
