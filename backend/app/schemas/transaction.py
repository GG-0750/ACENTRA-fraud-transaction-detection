from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TransactionBase(BaseModel):
    customer_id: str
    amount: float
    timestamp: datetime
    location: str
    merchant: Optional[str] = None
    channel: Optional[str] = None


class TransactionCreate(TransactionBase):
    pass


class TransactionRead(TransactionBase):
    id: int
    status: str
    review_status_id: int
    created_at: datetime
    fraud_flags: List[Dict[str, Any]] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ReviewUpdate(BaseModel):
    action: str
    reviewer_note: Optional[str] = None
