from pydantic import BaseModel, ConfigDict, Field, model_validator


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    description: str | None = None
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = None
    sort_order: int | None = None

    @model_validator(mode="after")
    def validate_update_fields(self) -> "CategoryUpdate":
        if not self.model_fields_set:
            raise ValueError("至少提供一个需要更新的字段")
        if any(
            getattr(self, field) is None and field != "description"
            for field in self.model_fields_set
        ):
            raise ValueError("更新字段不能为 null")
        return self


class CategoryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    sort_order: int
