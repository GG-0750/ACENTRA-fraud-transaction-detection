from abc import ABC, abstractmethod
from typing import Optional


class NotificationService(ABC):
    @abstractmethod
    def send(self, title: str, message: str, severity: str, transaction_id: Optional[int] = None):
        raise NotImplementedError
