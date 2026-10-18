from typing import Any

from pydantic import BaseModel


class ApiResponse(BaseModel):
    """统一封装的返回格式"""
    code: int
    message: str
    data: Any = None

    @classmethod
    def success(
        cls,
        message: str = "请求成功",
        data: Any = None,
        code: int = 200,
    ) -> "ApiResponse":
        return cls(code=code, message=message, data=data)

    @classmethod
    def error(cls, code: int = 500, message: str = "请求失败") -> "ApiResponse":
        return cls(code=code, message=message)
