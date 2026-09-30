from datetime import datetime

from sqlalchemy import Column, DateTime, String

from app.core.database import Base


class DatabaseMigration(Base):
    __tablename__ = "database_migrations"

    id = Column(String(120), primary_key=True)
    applied_at = Column(DateTime, default=datetime.utcnow, nullable=False)