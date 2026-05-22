from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _normalize_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return value


class AccountCreate(BaseModel):
    region_code: Optional[str] = Field(None, description="RU/TR/US/EU")
    login_name: Optional[str] = None
    domain_code: Optional[str] = Field(None, description="email domain, e.g. example.com")
    account_date: Optional[date] = None
    notes: Optional[str] = None

    @field_validator("account_date", mode="before")
    @classmethod
    def normalize_account_date(cls, v):
        return _normalize_date(v)


class AccountUpdate(BaseModel):
    region_code: Optional[str] = None
    login_name: Optional[str] = None
    domain_code: Optional[str] = None
    status_code: Optional[str] = None
    is_deactivated: Optional[bool] = None
    account_date: Optional[date] = None
    notes: Optional[str] = None

    @field_validator("account_date", mode="before")
    @classmethod
    def normalize_account_date(cls, v):
        return _normalize_date(v)


class AccountPlatformSlots(BaseModel):
    platform_code: str
    slot_capacity: int
    occupied_slots: int
    free_slots: int


class AccountSlotStatusOut(BaseModel):
    slot_type_code: str
    platform_code: str
    mode: str
    capacity: int
    occupied: int
    free: int


class AccountOut(BaseModel):
    account_id: int
    region_code: Optional[str]
    status: str
    login_name: Optional[str]
    domain_code: Optional[str]
    login_full: Optional[str]
    platform_slots: List[AccountPlatformSlots]
    slot_status: List[AccountSlotStatusOut] = []
    product_titles: Optional[List[str]] = None
    platform_codes: Optional[List[str]] = None
    account_date: Optional[date] = None
    notes: Optional[str] = None
    is_deactivated: bool = False
    deactivated_at: Optional[datetime] = None
    next_activation_at: Optional[datetime] = None


class AccountListOut(BaseModel):
    total: int
    items: List[AccountOut]


class AccountSecretIn(BaseModel):
    secret_key: str
    secret_value: str


class AccountSecretOut(BaseModel):
    secret_key: str
    secret_value_b64: str
    created_at: datetime


class AccountSecretsBatchIn(BaseModel):
    account_ids: List[int]


class AccountSecretsBatchItem(BaseModel):
    account_id: int
    secrets: List[AccountSecretOut]


class AccountSecretPatchItemIn(BaseModel):
    secret_key: str
    secret_value: str


class AccountSecretsPatchIn(BaseModel):
    upserts: List[AccountSecretPatchItemIn] = Field(default_factory=list)
    delete_keys: List[str] = Field(default_factory=list)


class SlotAvailabilityOut(BaseModel):
    slot_type_code: str
    has_free: bool


class AccountProductsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_ids: Optional[List[int]] = None


class AccountLabelOut(BaseModel):
    account_id: int
    login_name: Optional[str] = None
    domain_code: Optional[str] = None
    login_full: Optional[str] = None


class ProductAccountOut(BaseModel):
    deal_item_id: int
    account_id: int
    login_full: Optional[str]
    customer_nickname: Optional[str] = None
    deal_date: Optional[datetime] = None


class ProductLinkedAccountOut(BaseModel):
    account_id: int
    login_name: str
    domain_code: str
    login_full: str


class ProductSelectableAccountOut(BaseModel):
    account_id: int
    login_name: str
    domain_code: str
    login_full: str


class AccountProductOut(BaseModel):
    product_id: int
    type_code: str
    title: str
    short_title: Optional[str] = None
    region_code: Optional[str] = None
    platform_codes: List[str] = Field(default_factory=list)


class SlotTypeOut(BaseModel):
    code: str
    name: str
    platform_code: str
    mode: str
    capacity: int


class AccountSlotAssignmentOut(BaseModel):
    assignment_id: int
    account_id: int
    account_login: Optional[str] = None
    slot_type_code: str
    customer_id: Optional[int]
    customer_nickname: Optional[str]
    product_id: Optional[int] = None
    product_title: Optional[str] = None
    deal_id: Optional[int]
    deal_item_id: Optional[int]
    assigned_at: datetime
    released_at: Optional[datetime]
    assigned_by: Optional[str]
    released_by: Optional[str]
