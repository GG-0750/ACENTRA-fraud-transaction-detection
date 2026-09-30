from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.notification import Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def list_notifications(db: Session = Depends(get_db)):
    notifications = db.query(Notification).order_by(Notification.created_at.desc()).all()
    return [
        {
            "id": item.id,
            "title": item.title,
            "message": item.message,
            "severity": item.severity,
            "transaction_id": item.transaction_id,
            "created_at": item.created_at.isoformat(),
            "is_demo": item.is_demo,
            "email_status": item.email_status,
            "email_recipient": item.email_recipient,
        }
        for item in notifications
    ]
