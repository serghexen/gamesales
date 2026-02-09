from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


class SalesAnalyticsTotals(BaseModel):
    revenue: float
    purchase_cost: float
    margin: float
    count: int
    avg_check: float


class SalesAnalyticsPoint(BaseModel):
    date: date
    revenue: float
    purchase_cost: float
    margin: float
    count: int


class SalesAnalyticsByType(BaseModel):
    deal_type_code: str
    revenue: float
    purchase_cost: float
    margin: float
    count: int


class SalesAnalyticsOut(BaseModel):
    totals: SalesAnalyticsTotals
    by_day: List[SalesAnalyticsPoint]
    by_type: List[SalesAnalyticsByType]


class SourceAnalyticsItem(BaseModel):
    source_id: Optional[int]
    source_code: Optional[str]
    source_name: Optional[str]
    deals_count: int
    revenue: float


class RepeatCustomersOut(BaseModel):
    repeat_count: int
    total_customers: int
    repeat_share: float


class SourcesAnalyticsOut(BaseModel):
    top_by_count: List[SourceAnalyticsItem]
    top_by_revenue: List[SourceAnalyticsItem]
    repeat_customers: RepeatCustomersOut


class AuditItemOut(BaseModel):
    deal_id: Optional[int]
    table_name: str
    action: str
    changed_at: datetime
    changed_by: Optional[str]


class AuditAnalyticsOut(BaseModel):
    total: int
    items: List[AuditItemOut]
