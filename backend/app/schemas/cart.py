from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.dish import DishPublic


class CartItemAdd(BaseModel):
    dish_id: int = Field(gt=0)
    quantity: int = Field(default=1, gt=0)


class CartItemQuantityUpdate(BaseModel):
    quantity: int = Field(gt=0)


class CartItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dish_id: int
    quantity: int
    dish: DishPublic


class CartPublic(BaseModel):
    items: list[CartItemPublic]
    total_quantity: int
    total_amount: Decimal
