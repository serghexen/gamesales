from typing import List, Optional

from pydantic import BaseModel


class ImportIssue(BaseModel):
    row: int
    field: str
    value: Optional[str] = None
    message: str


class ImportReportIn(BaseModel):
    errors: List[ImportIssue] = []
    warnings: List[ImportIssue] = []
