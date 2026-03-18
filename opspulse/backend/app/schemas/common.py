from pydantic import BaseModel
from typing import Optional, Generic, TypeVar, List
from datetime import date

T = TypeVar("T")


class DateRangeFilter(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    department_id: Optional[int] = None
    location_id: Optional[int] = None


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int
