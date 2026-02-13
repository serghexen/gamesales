from datetime import datetime, timezone, date
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


def _normalize_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    return value


class RentalCreate(BaseModel):
    account_id: int
    customer_nickname: str
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    slots_used: int = 1
    price: float = 0
    product_id: Optional[int] = None
    platform_code: Optional[str] = None
    slot_type_code: Optional[str] = None
    source_id: Optional[int] = None
    purchase_at: Optional[datetime] = None

    @field_validator("purchase_at", "start_at", "end_at", mode="before")
    @classmethod
    def normalize_dt(cls, v):
        return _normalize_datetime(v)


class DealCreate(BaseModel):
    deal_type_code: str = Field(..., description="sale/rental")
    account_id: Optional[int] = None
    product_id: Optional[int] = None
    customer_nickname: Optional[str] = None
    order_number: Optional[str] = None
    responsible_username: Optional[str] = None
    source_id: Optional[int] = None
    login: Optional[str] = None
    password: Optional[str] = None
    region_code: Optional[str] = None
    platform_code: Optional[str] = None
    slot_type_code: Optional[str] = None
    price: float = 0
    purchase_cost: float = 0
    product_link: Optional[str] = None
    purchase_at: Optional[datetime] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    slots_used: int = 1
    notes: Optional[str] = None
    flow_status_code: Optional[str] = None

    @field_validator("purchase_at", "start_at", "end_at", mode="before")
    @classmethod
    def normalize_dt(cls, v):
        return _normalize_datetime(v)


class DealUpdate(BaseModel):
    deal_type_code: Optional[str] = None
    account_id: Optional[int] = None
    product_id: Optional[int] = None
    customer_nickname: Optional[str] = None
    order_number: Optional[str] = None
    responsible_username: Optional[str] = None
    source_id: Optional[int] = None
    login: Optional[str] = None
    password: Optional[str] = None
    region_code: Optional[str] = None
    platform_code: Optional[str] = None
    slot_type_code: Optional[str] = None
    price: Optional[float] = None
    purchase_cost: Optional[float] = None
    product_link: Optional[str] = None
    purchase_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    slots_used: Optional[int] = None
    notes: Optional[str] = None
    flow_status_code: Optional[str] = None
    is_refund: Optional[bool] = None

    @field_validator("purchase_at", "created_at", "completed_at", "start_at", "end_at", mode="before")
    @classmethod
    def normalize_dt(cls, v):
        return _normalize_datetime(v)


class DealListItem(BaseModel):
    deal_id: int
    deal_type: str
    deal_type_code: Optional[str] = None
    status: str
    flow_status: Optional[str] = None
    flow_status_code: Optional[str] = None
    account_id: Optional[int] = None
    account_login: Optional[str]
    region_code: Optional[str]
    product_id: Optional[int] = None
    product_title: Optional[str] = None
    product_short_title: Optional[str] = None
    platform_code: Optional[str]
    slot_type_code: Optional[str] = None
    customer_nickname: Optional[str]
    login: Optional[str] = None
    password: Optional[str] = None
    order_number: Optional[str] = None
    responsible_username: Optional[str] = None
    source_id: Optional[int]
    price: float
    purchase_cost: Optional[float] = None
    product_link: Optional[str] = None
    purchase_at: Optional[datetime]
    created_at: datetime
    completed_at: Optional[datetime] = None
    slots_used: Optional[int] = None
    notes: Optional[str] = None
    is_refund: bool = False


class DealListOut(BaseModel):
    total: int
    items: List[DealListItem]
