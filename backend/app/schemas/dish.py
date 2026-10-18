from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.category import CategoryPublic


class DishCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    image_url: str | None = Field(default=None, max_length=500)
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    stock: int = Field(default=0, ge=0)
    description: str | None = None
    category_id: int = Field(gt=0)
    is_available: bool = True


class DishUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    image_url: str | None = Field(default=None, max_length=500)
    price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    stock: int | None = Field(default=None, ge=0)
    description: str | None = None
    category_id: int | None = Field(default=None, gt=0)
    is_available: bool | None = None

    @model_validator(mode="after")
    def validate_update_fields(self) -> "DishUpdate":
        if not self.model_fields_set:
            raise ValueError("至少提供一个需要更新的字段")
        if any(
            getattr(self, field) is None
            for field in self.model_fields_set
            if field not in {"image_url", "description"}
        ):
            raise ValueError("更新字段不能为 null")
        return self


class DishAvailabilityUpdate(BaseModel):
    is_available: bool


class DishPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    image_url: str | None
    price: Decimal
    stock: int
    description: str | None
    category_id: int
    is_available: bool
    category: CategoryPublic
