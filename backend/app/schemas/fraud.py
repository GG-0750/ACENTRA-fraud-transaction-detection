from typing import Any, Dict, List

from pydantic import BaseModel, Field


class FraudFlagCreate(BaseModel):
    transaction_id: int
    rule_name: str
    triggered: bool = True
    severity: str = "MEDIUM"
    reason: str
    evidence: Dict[str, Any] = Field(default_factory=dict)


class FraudFlagRead(BaseModel):
    id: int
    transaction_id: int
    rule_name: str
    triggered: bool
    severity: str
    reason: str
    evidence: Dict[str, Any]

    class Config:
        from_attributes = True


class RuleImpactSummary(BaseModel):
    total_transactions: int
    transactions_flagged: int
    velocity_rule_count: int
    amount_rule_count: int
    location_rule_count: int
    multi_rule_transactions: int
    severity_breakdown: Dict[str, int]


class PlaygroundSimulation(BaseModel):
    rule_name: str
    window_minutes: int = 30
    threshold_count: int = 4
    min_distance_kmh: float = 700.0
    amount_multiplier: float = 3.0
    affected_transaction_ids: List[int] = Field(default_factory=list)
    new_flags_count: int = 0
