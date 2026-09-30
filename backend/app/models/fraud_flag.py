from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class FraudFlag(Base):
    __tablename__ = "fraud_flags"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, index=True)
    rule_name = Column(String(80), nullable=False)
    severity = Column(String(20), nullable=False)
    triggered = Column(Integer, default=1)
    reason = Column(Text, nullable=False)
    evidence = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    transaction = relationship("Transaction", back_populates="fraud_flags")
