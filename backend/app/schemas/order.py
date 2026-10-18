from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

OrderStatus = Literal[
    "pending_payment",
    "pending_acceptance",
    "pending_delivery",
    "completed",
    "cancelled",
]


class OrderCreate(BaseModel):
    address_id: int = Field(gt=0)


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dish_id: int | None
    dish_name: str
    dish_image_url: str | None
    category_name: str
    unit_price: Decimal
    quantity: int
    subtotal: Decimal


class OrderPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_no: str
    status: OrderStatus
    recipient_name: str
    recipient_phone: str
    province: str
    city: str
    district: str
    address_detail: str
    dish_amount: Decimal
    delivery_fee: Decimal
    total_amount: Decimal
    create_time: datetime
    items: list[OrderItemPublic]
