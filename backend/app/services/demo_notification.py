from typing import Optional

from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.services.notification_service import NotificationService


class DemoNotificationService(NotificationService):
    def __init__(self, db: Session):
        self.db = db

    def send(self, title: str, message: str, severity: str, transaction_id: Optional[int] = None):
        notification = Notification(
            title=title,
            message=message,
            severity=severity,
            transaction_id=transaction_id,
            is_demo=True,
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification
