from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.coupon import normalize_utc


class SeckillActivityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    dish_id: int = Field(gt=0)
    sale_price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    stock: int = Field(gt=0, le=1_000_000)
    limit_per_user: int = Field(default=1, ge=1, le=100)
    start_time: datetime
    end_time: datetime
    is_active: bool = True

    @field_validator("start_time", "end_time")
    @classmethod
    def use_utc(cls, value: datetime) -> datetime:
        return normalize_utc(value)

    @model_validator(mode="after")
    def validate_time_range(self) -> "SeckillActivityCreate":
        if self.end_time <= self.start_time:
            raise ValueError("秒杀结束时间必须晚于开始时间")
        return self


class SeckillActivityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    sale_price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    stock: int | None = Field(default=None, gt=0, le=1_000_000)
    limit_per_user: int | None = Field(default=None, ge=1, le=100)
    start_time: datetime | None = None
    end_time: datetime | None = None
    is_active: bool | None = None

    @field_validator("start_time", "end_time")
    @classmethod
    def use_utc(cls, value: datetime | None) -> datetime | None:
        return normalize_utc(value) if value is not None else None

    @model_validator(mode="after")
    def validate_update(self) -> "SeckillActivityUpdate":
        if not self.model_fields_set:
            raise ValueError("至少提供一个需要更新的字段")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("更新字段不能为 null")
        return self


class SeckillActiveUpdate(BaseModel):
    is_active: bool


class SeckillActivityPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    dish_id: int
    dish_name: str
    dish_image_url: str | None
    original_price: Decimal
    sale_price: Decimal
    stock: int
    sold_count: int
    remaining_stock: int
    limit_per_user: int
    start_time: datetime
    end_time: datetime
    is_active: bool
    status: str
