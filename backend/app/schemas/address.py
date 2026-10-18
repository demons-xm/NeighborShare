from pydantic import BaseModel, ConfigDict, Field, model_validator


class AddressCreate(BaseModel):
    recipient_name: str = Field(min_length=1, max_length=50)
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    province: str = Field(min_length=1, max_length=50)
    city: str = Field(min_length=1, max_length=50)
    district: str = Field(min_length=1, max_length=50)
    detail: str = Field(min_length=1, max_length=255)
    is_default: bool = False


class AddressUpdate(BaseModel):
    recipient_name: str | None = Field(default=None, min_length=1, max_length=50)
    phone: str | None = Field(default=None, pattern=r"^1[3-9]\d{9}$")
    province: str | None = Field(default=None, min_length=1, max_length=50)
    city: str | None = Field(default=None, min_length=1, max_length=50)
    district: str | None = Field(default=None, min_length=1, max_length=50)
    detail: str | None = Field(default=None, min_length=1, max_length=255)
    is_default: bool | None = None

    @model_validator(mode="after")
    def validate_update_fields(self) -> "AddressUpdate":
        if not self.model_fields_set:
            raise ValueError("至少提供一个需要更新的字段")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("更新字段不能为 null")
        return self


class AddressPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recipient_name: str
    phone: str
    province: str
    city: str
    district: str
    detail: str
    is_default: bool
