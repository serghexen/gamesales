from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class FinanceSectionOut(BaseModel):
    section_id: int
    parent_section_id: Optional[int] = None
    type_id: Optional[int] = None
    type_code: Optional[str] = None
    type_name: Optional[str] = None
    code: str
    name: str
    kind: str
    sort_order: int = 0
    is_active: bool = True


class FinanceOperationOut(BaseModel):
    operation_id: int
    type_id: int
    code: str
    name: str
    input_mode: str
    requires_region: bool
    requires_source: bool
    requires_project: bool
    requires_qty: bool
    allows_negative: bool
    sort_order: int = 0
    is_active: bool = True


class FinanceProjectOut(BaseModel):
    project_id: int
    code: str
    name: str
    is_active: bool = True


class FinanceRegionOut(BaseModel):
    region_id: int
    code: str
    name: str
    is_active: bool = True


class FinanceSourceOut(BaseModel):
    source_id: int
    code: str
    name: str
    is_active: bool = True


class FinanceStatusOut(BaseModel):
    code: str
    name: str


class FinanceTypeOut(BaseModel):
    type_id: int
    code: str
    name: str
    sort_order: int = 0
    is_active: bool = True


class FinanceBootstrapOut(BaseModel):
    types: list[FinanceTypeOut] = Field(default_factory=list)
    sections: list[FinanceSectionOut] = Field(default_factory=list)
    operations: list[FinanceOperationOut] = Field(default_factory=list)
    projects: list[FinanceProjectOut] = Field(default_factory=list)
    regions: list[FinanceRegionOut] = Field(default_factory=list)
    sources: list[FinanceSourceOut] = Field(default_factory=list)
    statuses: list[FinanceStatusOut] = Field(default_factory=list)


class FinanceSectionCreateIn(BaseModel):
    parent_section_id: Optional[int] = None
    type_id: Optional[int] = None
    code: str
    name: str
    kind: Optional[str] = None
    sort_order: int = 0


class FinanceTypeCreateIn(BaseModel):
    code: str
    name: str
    sort_order: int = 0


class FinanceTypeUpdateIn(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class FinanceSectionUpdateIn(BaseModel):
    parent_section_id: Optional[int] = None
    type_id: Optional[int] = None
    code: Optional[str] = None
    name: Optional[str] = None
    kind: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class FinanceOperationCreateIn(BaseModel):
    type_id: int
    code: str
    name: str
    input_mode: str = "manual"
    requires_region: bool = False
    requires_source: bool = False
    requires_project: bool = False
    requires_qty: bool = False
    allows_negative: bool = False
    sort_order: int = 0


class FinanceOperationUpdateIn(BaseModel):
    type_id: Optional[int] = None
    code: Optional[str] = None
    name: Optional[str] = None
    input_mode: Optional[str] = None
    requires_region: Optional[bool] = None
    requires_source: Optional[bool] = None
    requires_project: Optional[bool] = None
    requires_qty: Optional[bool] = None
    allows_negative: Optional[bool] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class FinanceProjectCreateIn(BaseModel):
    code: str
    name: str


class FinanceProjectUpdateIn(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    is_active: Optional[bool] = None


class FinanceFormulaCreateIn(BaseModel):
    operation_id: int
    version: int
    expression_json: dict = Field(default_factory=dict)
    rounding_mode: str = "half_up"
    scale: int = 2
    effective_from: date
    effective_to: Optional[date] = None
    is_active: bool = True
    comment: Optional[str] = None


class FinanceFormulaOut(BaseModel):
    formula_id: int
    operation_id: int
    version: int
    expression_json: dict = Field(default_factory=dict)
    rounding_mode: str
    scale: int
    effective_from: date
    effective_to: Optional[date] = None
    is_active: bool = True
    comment: Optional[str] = None
    created_by: str
    created_at: datetime


class FinanceEntryCreateIn(BaseModel):
    biz_date: date
    operation_id: int
    region_id: Optional[int] = None
    source_id: Optional[int] = None
    project_id: Optional[int] = None
    qty: Decimal = Decimal("1")
    amount: Decimal
    currency: str = "RUB"
    input_channel: str = "manual"
    external_key: Optional[str] = None
    status_code: str = "confirmed"
    comment: Optional[str] = None
    payload_json: dict = Field(default_factory=dict)
    app_deal_id: Optional[int] = None
    app_deal_item_id: Optional[int] = None


class FinanceEntryOut(BaseModel):
    entry_id: int
    biz_date: date
    operation_id: int
    region_id: Optional[int] = None
    source_id: Optional[int] = None
    project_id: Optional[int] = None
    qty: Decimal
    amount: Decimal
    currency: str
    input_channel: str
    external_key: Optional[str] = None
    status_code: str
    comment: Optional[str] = None
    created_by: str
    created_at: datetime
    updated_at: datetime


class FinanceEntryListOut(BaseModel):
    total: int
    items: list[FinanceEntryOut] = Field(default_factory=list)


class FinanceEntryBulkIn(BaseModel):
    items: list[FinanceEntryCreateIn] = Field(default_factory=list)
    stop_on_error: bool = False
    file_name: Optional[str] = None


class FinanceEntryBulkErrorOut(BaseModel):
    row_no: int
    error: str
    external_key: Optional[str] = None


class FinanceEntryBulkOut(BaseModel):
    batch_id: int
    total_rows: int
    success_rows: int
    failed_rows: int
    status: str
    errors: list[FinanceEntryBulkErrorOut] = Field(default_factory=list)


class FinanceCatalogSyncOut(BaseModel):
    regions_synced: int = 0
    sources_synced: int = 0


class FinanceSeedDefaultsOut(BaseModel):
    sections_seeded: int = 0
    operations_seeded: int = 0
    projects_seeded: int = 0


class FinancePnlTotalsOut(BaseModel):
    revenue: Decimal = Decimal("0")
    direct_expense: Decimal = Decimal("0")
    indirect_expense: Decimal = Decimal("0")
    gross_profit: Decimal = Decimal("0")
    operating_profit: Decimal = Decimal("0")
    margin: Decimal = Decimal("0")


class FinancePnlBucketOut(BaseModel):
    bucket: str
    revenue: Decimal = Decimal("0")
    direct_expense: Decimal = Decimal("0")
    indirect_expense: Decimal = Decimal("0")
    gross_profit: Decimal = Decimal("0")
    operating_profit: Decimal = Decimal("0")
    margin: Decimal = Decimal("0")


class FinancePnlOut(BaseModel):
    totals: FinancePnlTotalsOut
    series: list[FinancePnlBucketOut] = Field(default_factory=list)


class FinanceProjectsReportRowOut(BaseModel):
    project_id: Optional[int] = None
    project_code: str
    project_name: str
    source_id: Optional[int] = None
    source_code: Optional[str] = None
    source_name: Optional[str] = None
    revenue: Decimal = Decimal("0")
    direct_expense: Decimal = Decimal("0")
    indirect_expense: Decimal = Decimal("0")
    gross_profit: Decimal = Decimal("0")
    operating_profit: Decimal = Decimal("0")
    margin: Decimal = Decimal("0")


class FinanceProjectsReportOut(BaseModel):
    totals: FinancePnlTotalsOut
    items: list[FinanceProjectsReportRowOut] = Field(default_factory=list)
