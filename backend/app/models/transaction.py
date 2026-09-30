from datetime import datetime

from sqlalchemy import Column, Float, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship

from app.core.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(String(50), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    location = Column(String(120), nullable=False)
    merchant = Column(String(120), nullable=True)
    channel = Column(String(50), nullable=True)
    status = Column(String(50), nullable=False, default="pending", index=True)
    review_status_id = Column(Integer, ForeignKey("review_statuses.id"), default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    review_status = relationship("ReviewStatus")
    fraud_flags = relationship("FraudFlag", back_populates="transaction", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="transaction")
