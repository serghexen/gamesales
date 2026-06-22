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
    source_id: Optional[int] = None
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
    source_id: Optional[int] = None
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
    source_id: Optional[int] = None
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


class FinanceYandexSyncIn(BaseModel):
    date_from: date
    date_to: date
    store_code: str = "asat"


class FinanceYandexSyncOut(BaseModel):
    provider: str = "yandex_market"
    store_code: str = "asat"
    date_from: date
    date_to: date
    total_rows: int = 0
    created_rows: int = 0
    updated_rows: int = 0
    skipped_rows: int = 0
    failed_rows: int = 0
    errors: list[FinanceEntryBulkErrorOut] = Field(default_factory=list)


class FinanceYandexSyncJobOut(BaseModel):
    job_id: str
    status: str
    message: Optional[str] = None
    result: Optional[FinanceYandexSyncOut] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class FinanceWildberriesSyncIn(BaseModel):
    date_from: date
    date_to: date
    store_code: str = "asat"


class FinanceWildberriesSyncOut(BaseModel):
    provider: str = "wildberries"
    store_code: str = "asat"
    date_from: date
    date_to: date
    total_rows: int = 0
    created_rows: int = 0
    updated_rows: int = 0
    skipped_rows: int = 0
    failed_rows: int = 0
    errors: list[FinanceEntryBulkErrorOut] = Field(default_factory=list)


class FinanceWildberriesSyncJobOut(BaseModel):
    job_id: str
    status: str
    message: Optional[str] = None
    result: Optional[FinanceWildberriesSyncOut] = None
    error: Optional[str] = None
    retry_after_seconds: int = 0
    created_at: datetime
    updated_at: datetime


class FinanceOzonSyncIn(BaseModel):
    date_from: date
    date_to: date
    store_code: str = "asat"


class FinanceOzonSyncOut(BaseModel):
    provider: str = "ozon"
    store_code: str = "asat"
    date_from: date
    date_to: date
    total_rows: int = 0
    created_rows: int = 0
    updated_rows: int = 0
    skipped_rows: int = 0
    failed_rows: int = 0
    errors: list[FinanceEntryBulkErrorOut] = Field(default_factory=list)


class FinanceOzonSyncJobOut(BaseModel):
    job_id: str
    status: str
    message: Optional[str] = None
    result: Optional[FinanceOzonSyncOut] = None
    error: Optional[str] = None
    retry_after_seconds: int = 0
    created_at: datetime
    updated_at: datetime


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


class FinanceSourcesReportRowOut(BaseModel):
    source_id: Optional[int] = None
    source_code: Optional[str] = None
    source_name: Optional[str] = None
    region_id: Optional[int] = None
    region_code: Optional[str] = None
    region_name: Optional[str] = None
    operation_code: Optional[str] = None
    operation_name: Optional[str] = None
    revenue: Decimal = Decimal("0")
    direct_expense: Decimal = Decimal("0")
    cash_flow: Decimal = Decimal("0")
    deals_count: int = 0


class FinanceSourcesReportOut(BaseModel):
    totals: FinancePnlTotalsOut
    items: list[FinanceSourcesReportRowOut] = Field(default_factory=list)


class FinanceSourcesReportDetailRowOut(BaseModel):
    row_type: str
    deal_id: Optional[int] = None
    entry_id: Optional[int] = None
    activity_date: date
    customer_name: Optional[str] = None
    source_id: Optional[int] = None
    source_code: Optional[str] = None
    source_name: Optional[str] = None
    region_id: Optional[int] = None
    region_code: Optional[str] = None
    region_name: Optional[str] = None
    operation_name: Optional[str] = None
    item_title: Optional[str] = None
    qty: Decimal = Decimal("0")
    revenue: Decimal = Decimal("0")
    purchase_cost: Decimal = Decimal("0")
    purchase_cost_rate: Optional[Decimal] = None
    direct_expense: Decimal = Decimal("0")
    cash_flow: Decimal = Decimal("0")
    comment: Optional[str] = None
    external_key: Optional[str] = None
    order_ids: list[str] = Field(default_factory=list)
    shop_skus: list[str] = Field(default_factory=list)
    orders_count: int = 0
    rows_count: int = 0
    reason: Optional[str] = None


class FinanceSourcesReportDetailTotalsOut(FinancePnlTotalsOut):
    purchase_cost: Decimal = Decimal("0")


class FinanceSourcesReportDetailsOut(BaseModel):
    title: str
    totals: FinanceSourcesReportDetailTotalsOut
    items: list[FinanceSourcesReportDetailRowOut] = Field(default_factory=list)


class FinanceCashFlowLineOut(BaseModel):
    name: str
    amount: Decimal = Decimal("0")


class FinanceCashFlowDetailRowOut(BaseModel):
    row_type: str
    line_type: str
    line_name: str
    activity_date: date
    deal_id: Optional[int] = None
    entry_id: Optional[int] = None
    customer_name: Optional[str] = None
    operation_name: Optional[str] = None
    item_title: Optional[str] = None
    region_id: Optional[int] = None
    region_code: Optional[str] = None
    region_name: Optional[str] = None
    source_id: Optional[int] = None
    source_code: Optional[str] = None
    source_name: Optional[str] = None
    qty: Decimal = Decimal("0")
    amount: Decimal = Decimal("0")
    comment: Optional[str] = None
    external_key: Optional[str] = None
    order_ids: list[str] = Field(default_factory=list)
    shop_skus: list[str] = Field(default_factory=list)
    orders_count: int = 0
    rows_count: int = 0
    created_by: Optional[str] = None
    reason: Optional[str] = None


class FinanceCashFlowTotalsOut(BaseModel):
    revenue: Decimal = Decimal("0")
    expense: Decimal = Decimal("0")
    cash_flow: Decimal = Decimal("0")
    opening_balance: Decimal = Decimal("0")
    current_balance: Decimal = Decimal("0")
    opening_balance_month: Optional[date] = None
    opening_balance_manual: bool = False


class FinanceCashFlowDetailsOut(BaseModel):
    title: str
    totals: FinanceCashFlowTotalsOut
    items: list[FinanceCashFlowDetailRowOut] = Field(default_factory=list)


class FinanceCashFlowReportOut(BaseModel):
    totals: FinanceCashFlowTotalsOut
    revenues: list[FinanceCashFlowLineOut] = Field(default_factory=list)
    expenses: list[FinanceCashFlowLineOut] = Field(default_factory=list)


class FinanceCashFlowOpeningBalanceIn(BaseModel):
    month: str
    amount: Decimal
    comment: Optional[str] = None


class FinanceCashFlowOpeningBalanceOut(BaseModel):
    month: date
    amount: Decimal
    comment: Optional[str] = None
    updated_at: datetime


class FinanceCardBalanceSetIn(BaseModel):
    amount: Decimal
    comment: Optional[str] = None


class FinanceCardBalanceOut(BaseModel):
    card_code: str
    region_code: str
    currency: str
    snapshot_balance: Decimal = Decimal("0")
    spent_after_snapshot: Decimal = Decimal("0")
    current_balance: Decimal = Decimal("0")
    snapshot_at: Optional[datetime] = None
    snapshot_manual: bool = False
    comment: Optional[str] = None
