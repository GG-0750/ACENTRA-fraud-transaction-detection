from fastapi import APIRouter, Depends, HTTPException
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.fraud_engine import FraudEngine

router = APIRouter(prefix="/rules", tags=["rules"])


class PlaygroundRequest(BaseModel):
    rule_name: Literal["Velocity Rule", "Amount Rule", "Location Rule"]
    threshold_count: int = Field(default=4, ge=1)
    window_minutes: int = Field(default=30, ge=1)
    amount_multiplier: float = Field(default=3.0, gt=0)
    speed_threshold_kmh: float = Field(default=700.0, gt=0)


@router.get("")
def list_rules():
    return [
        {"rule_name": "Velocity Rule", "description": "Detect unusually high transaction frequency in a short time window."},
        {"rule_name": "Amount Rule", "description": "Detect amounts materially outside a customer normal range."},
        {"rule_name": "Location Rule", "description": "Detect implausible travel between locations over a short time."},
    ]


@router.post("/playground/simulate")
def simulate_rule(payload: PlaygroundRequest, db: Session = Depends(get_db)):
    engine = FraudEngine()
    results = engine.simulate_rule(
        db,
        payload.rule_name,
        payload.threshold_count,
        payload.window_minutes,
        payload.amount_multiplier,
        payload.speed_threshold_kmh,
    )
    return {
        "rule_name": results["rule_name"],
        "affected_transaction_ids": results["affected_transaction_ids"],
        "new_flags_count": results["new_flags_count"],
        "new_rule_triggers_count": results["new_rule_triggers_count"],
        "affected_count": results["affected_count"],
        "newly_flagged_transaction_ids": results["newly_flagged_transaction_ids"],
        "sample_transaction_ids": results["sample_transaction_ids"],
        "threshold_count": payload.threshold_count,
        "window_minutes": payload.window_minutes,
        "amount_multiplier": payload.amount_multiplier,
        "speed_threshold_kmh": payload.speed_threshold_kmh,
    }
