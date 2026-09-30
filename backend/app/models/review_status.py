from sqlalchemy import Column, Integer, String

from app.core.database import Base


class ReviewStatus(Base):
    __tablename__ = "review_statuses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
