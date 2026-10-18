from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ShopUpdate(BaseModel):
    shop_name: str | None = Field(default=None, min_length=1, max_length=100)
    logo_url: str | None = Field(default=None, max_length=500)
    description: str | None = None
    business_hours: str | None = Field(default=None, min_length=1, max_length=100)
    delivery_range: str | None = Field(default=None, max_length=255)
    minimum_order_amount: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    delivery_fee: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    is_open: bool | None = None

    @model_validator(mode="after")
    def validate_update_fields(self) -> "ShopUpdate":
        if not self.model_fields_set:
            raise ValueError("至少提供一个需要更新的字段")
        if any(
            getattr(self, field) is None and field != "logo_url"
            for field in self.model_fields_set
        ):
            raise ValueError("更新字段不能为 null")
        return self


class ShopPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shop_name: str
    logo_url: str | None
    description: str
    business_hours: str
    delivery_range: str
    minimum_order_amount: Decimal
    delivery_fee: Decimal
    is_open: bool
