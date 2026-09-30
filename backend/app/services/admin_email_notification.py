from email.message import EmailMessage
import logging
import smtplib
import ssl
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.notification import Notification
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class AdminEmailNotificationService(NotificationService):
    """Persist every alert locally and email configured admins for high-risk cases."""

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def send(self, title: str, message: str, severity: str, transaction_id: Optional[int] = None):
        is_high_risk = severity.upper() in {"HIGH", "CRITICAL"}
        notification = Notification(
            title=title,
            message=message,
            severity=severity,
            transaction_id=transaction_id,
            is_demo=True,
            email_status="not_configured" if is_high_risk else "not_required",
            email_recipient=self.settings.fraud_alert_admin_email if is_high_risk else None,
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)

        if not is_high_risk:
            return notification

        required = (
            self.settings.smtp_host,
            self.settings.smtp_from_email,
            self.settings.fraud_alert_admin_email,
        )
        if not all(required):
            logger.warning(
                "High-risk alert TX%s persisted, but email is not configured. Set SMTP_HOST, SMTP_FROM_EMAIL, and FRAUD_ALERT_ADMIN_EMAIL.",
                transaction_id,
            )
            return notification

        email = EmailMessage()
        email["Subject"] = f"[ACENTRA {severity.upper()}] {title}"
        email["From"] = self.settings.smtp_from_email
        email["To"] = self.settings.fraud_alert_admin_email
        email.set_content(
            f"ACENTRA detected a {severity.upper()} risk transaction.\n\n"
            f"Transaction ID: {transaction_id}\n{message}\n\n"
            "Open ACENTRA to investigate the transaction and review the rule evidence."
        )

        try:
            context = ssl.create_default_context()
            if self.settings.smtp_ssl:
                with smtplib.SMTP_SSL(self.settings.smtp_host, self.settings.smtp_port, context=context, timeout=15) as smtp:
                    self._authenticate(smtp)
                    smtp.send_message(email)
            else:
                with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=15) as smtp:
                    smtp.ehlo()
                    if self.settings.smtp_starttls:
                        smtp.starttls(context=context)
                        smtp.ehlo()
                    self._authenticate(smtp)
                    smtp.send_message(email)
            notification.email_status = "sent"
            notification.is_demo = False
            self.db.commit()
        except (OSError, smtplib.SMTPException):
            logger.exception("Could not send ACENTRA high-risk email for transaction %s", transaction_id)
            notification.email_status = "failed"
            self.db.commit()
        return notification

    def _authenticate(self, smtp):
        if self.settings.smtp_username:
            smtp.login(self.settings.smtp_username, self.settings.smtp_password or "")