from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NotificationRead(BaseModel):
    id: int
    title: str
    message: str
    severity: str
    transaction_id: Optional[int] = None
    created_at: datetime
    is_demo: bool
    email_status: str = "not_required"
    email_recipient: Optional[str] = None

    class Config:
        from_attributes = True
