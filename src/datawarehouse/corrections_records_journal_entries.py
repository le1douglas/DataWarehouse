from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class CorrectionsRecordJournalEntries(BaseModel):
    entry_id: str
    date_time: datetime
    subject: Optional[str] = None
    type: Optional[str] = None
    ml: Optional[Decimal] = None
    ec: Optional[Decimal] = None
    ph: Optional[Decimal] = None
    temp: Optional[Decimal] = None
    notes: Optional[str] = None
    room: Optional[str] = None

    meta_extract_date_time: datetime
    meta_source: str
    meta_silver_date_time: datetime
    meta_reviewed_by: str
    meta_reviewed_date_time: datetime
