from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.fraud_flag import FraudFlag
from app.models.notification import Notification
from app.models.transaction import Transaction
from app.services.fraud_engine import FraudEngine

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    total_transactions = db.query(Transaction).count()
    flagged_transactions = db.query(Transaction).filter(Transaction.fraud_flags.any()).count()
    high_critical = sum(
        1 for tx in db.query(Transaction).filter(Transaction.fraud_flags.any()).all()
        if len({flag.rule_name for flag in tx.fraud_flags}) >= 2
        or any(flag.severity in {"HIGH", "CRITICAL"} for flag in tx.fraud_flags)
    )
    reviewed = db.query(Transaction).filter(Transaction.status.in_(["reviewed", "cleared"])).count()
    pending = db.query(Transaction).filter(Transaction.status == "pending").count()

    flags = db.query(FraudFlag).all()
    tx_rules = {}
    for flag in flags:
        tx_rules.setdefault(flag.transaction_id, set()).add(flag.rule_name)
    rule_counts = {
        "Velocity Rule": sum("Velocity Rule" in rules for rules in tx_rules.values()),
        "Amount Rule": sum("Amount Rule" in rules for rules in tx_rules.values()),
        "Location Rule": sum("Location Rule" in rules for rules in tx_rules.values()),
    }
    severity_breakdown = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    for tx in db.query(Transaction).all():
        tx_rules = {flag.rule_name for flag in tx.fraud_flags}
        if not tx_rules:
            severity_breakdown["LOW"] += 1
        elif len(tx_rules) >= 3 or any(flag.severity == "CRITICAL" for flag in tx.fraud_flags):
            severity_breakdown["CRITICAL"] += 1
        elif len(tx_rules) >= 2 or any(flag.severity == "HIGH" for flag in tx.fraud_flags):
            severity_breakdown["HIGH"] += 1
        else:
            severity_breakdown["MEDIUM"] += 1

    recent_alerts = (
        db.query(Transaction)
        .filter(Transaction.fraud_flags.any())
        .order_by(Transaction.timestamp.desc())
        .limit(5)
        .all()
    )

    return {
        "total_transactions": total_transactions,
        "flagged_transactions": flagged_transactions,
        "high_critical_cases": high_critical,
        "reviewed_cases": reviewed,
        "pending_cases": pending,
        "notification_count": db.query(Notification).count(),
        "rule_summary": rule_counts,
        "severity_breakdown": severity_breakdown,
        "recent_high_risk_cases": [
            {
                "transaction_id": tx.id,
                "customer_id": tx.customer_id,
                "amount": float(tx.amount),
                "timestamp": tx.timestamp.isoformat(),
                "location": tx.location,
                "severity": "CRITICAL" if len({f.rule_name for f in tx.fraud_flags}) >= 3 or any(f.severity == "CRITICAL" for f in tx.fraud_flags) else "HIGH" if len({f.rule_name for f in tx.fraud_flags}) >= 2 or any(f.severity == "HIGH" for f in tx.fraud_flags) else "MEDIUM",
                "review_status": tx.status,
                "rule_count": len({f.rule_name for f in tx.fraud_flags}),
            }
            for tx in recent_alerts
        ],
    }


@router.get("/rule-impact")
def rule_impact(db: Session = Depends(get_db)):
    engine = FraudEngine()
    impact = engine.analyze_rule_impact(db)
    return impact
