from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(120), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False, default="MEDIUM")
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_demo = Column(Boolean, default=True)
    email_status = Column(String(30), nullable=False, default="not_required")
    email_recipient = Column(String(254), nullable=True)
    transaction = relationship("Transaction", back_populates="notifications")
