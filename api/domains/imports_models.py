from typing import List, Optional

from pydantic import BaseModel


class ImportIssue(BaseModel):
    row: int
    sheet: Optional[str] = None
    account: Optional[str] = None
    field: str
    value: Optional[str] = None
    message: str


class ImportReportIn(BaseModel):
    errors: List[ImportIssue] = []
    warnings: List[ImportIssue] = []
