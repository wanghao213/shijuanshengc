"""通用响应模式."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageParams(BaseModel):
    """分页参数."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class ResponseMeta(BaseModel):
    """分页元信息."""

    page: int
    page_size: int
    total: int


class UnifiedResponse(BaseModel, Generic[T]):
    """统一响应格式."""

    code: int = 200
    message: str = "success"
    data: T | None = None
    meta: ResponseMeta | None = None


class ErrorDetail(BaseModel):
    """错误详情."""

    field: str
    message: str


class ErrorResponse(BaseModel):
    """错误响应."""

    code: int
    message: str
    errors: list[ErrorDetail] = []
