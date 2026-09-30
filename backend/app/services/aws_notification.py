import os
from typing import Optional

from app.services.notification_service import NotificationService


class AWSSESNotificationService(NotificationService):
    def __init__(self):
        self.access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.from_email = os.getenv("AWS_SES_FROM_EMAIL")

    def send(self, title: str, message: str, severity: str, transaction_id: Optional[int] = None):
        if not self.access_key or not self.secret_key or not self.from_email:
            raise RuntimeError("AWS SES configuration is missing; this service only works in a configured environment.")
        return {
            "provider": "AWS SES",
            "title": title,
            "message": message,
            "severity": severity,
            "transaction_id": transaction_id,
            "region": self.region,
        }


class AWSSNSNotificationService(NotificationService):
    def __init__(self):
        self.access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.topic_arn = os.getenv("AWS_SNS_TOPIC_ARN")

    def send(self, title: str, message: str, severity: str, transaction_id: Optional[int] = None):
        if not self.access_key or not self.secret_key or not self.topic_arn:
            raise RuntimeError("AWS SNS configuration is missing; this service only works in a configured environment.")
        return {
            "provider": "AWS SNS",
            "title": title,
            "message": message,
            "severity": severity,
            "transaction_id": transaction_id,
            "topic_arn": self.topic_arn,
            "region": self.region,
        }
