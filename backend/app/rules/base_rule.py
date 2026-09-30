from abc import ABC, abstractmethod
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class RuleResult(BaseModel):
    triggered: bool = False
    rule_name: str
    severity: str = "LOW"
    reason: str = ""
    evidence: Dict[str, Any] = Field(default_factory=dict)


class BaseRule(ABC):
    rule_name: str = "BaseRule"
    severity: str = "LOW"

    @abstractmethod
    def evaluate(self, transaction: Any, context: Dict[str, Any]) -> RuleResult:
        raise NotImplementedError

    def _historical_txns(self, transaction: Any, context: Dict[str, Any]) -> List[Any]:
        return context.get("customer_transactions", [])
