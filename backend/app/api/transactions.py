from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.fraud_flag import FraudFlag
from app.models.notification import Notification
from app.models.transaction import Transaction
from app.schemas.transaction import ReviewUpdate, TransactionCreate
from app.services.admin_email_notification import AdminEmailNotificationService
from app.services.fraud_engine import FraudEngine

router = APIRouter(prefix="/transactions", tags=["transactions"])


def get_severity(transaction: Transaction):
    flags = transaction.fraud_flags
    if len({flag.rule_name for flag in flags}) >= 3 or any(flag.severity == "CRITICAL" for flag in flags):
        return "CRITICAL"
    if len({flag.rule_name for flag in flags}) >= 2 or any(flag.severity == "HIGH" for flag in flags):
        return "HIGH"
    return "MEDIUM" if flags else "LOW"


def serialize_utc_datetime(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def serialize_transaction(transaction: Transaction, notification_status=None):
    return {
        "id": transaction.id,
        "customer_id": transaction.customer_id,
        "amount": float(transaction.amount),
        "timestamp": serialize_utc_datetime(transaction.timestamp),
        "location": transaction.location,
        "merchant": transaction.merchant,
        "channel": transaction.channel,
        "status": transaction.status,
        "review_status_id": transaction.review_status_id,
        "review_status": transaction.review_status.name if transaction.review_status else transaction.status,
        "severity": get_severity(transaction),
        "notification_status": notification_status or ("created" if any(n.transaction_id == transaction.id for n in transaction.notifications) else "not_applicable"),
        "email_notification_status": next((n.email_status for n in transaction.notifications if n.transaction_id == transaction.id), "not_applicable"),
        "created_at": serialize_utc_datetime(transaction.created_at),
        "fraud_flags": [
            {
                "id": flag.id,
                "transaction_id": flag.transaction_id,
                "rule_name": flag.rule_name,
                "severity": flag.severity,
                "triggered": bool(flag.triggered),
                "reason": flag.reason,
                "evidence": flag.evidence,
            }
            for flag in transaction.fraud_flags
        ],
    }


@router.get("")
def list_transactions(db: Session = Depends(get_db)):
    transactions = db.query(Transaction).order_by(Transaction.timestamp.desc()).all()
    return [serialize_transaction(tx) for tx in transactions]


@router.get("/flagged")
def get_flagged_transactions(db: Session = Depends(get_db)):
    transactions = db.query(Transaction).filter(Transaction.status == "flagged").order_by(Transaction.timestamp.desc()).all()
    return [serialize_transaction(tx) for tx in transactions]


@router.get("/{transaction_id}")
def get_transaction(transaction_id: int, db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return serialize_transaction(tx)


@router.get("/customer/{customer_id}/history")
def get_customer_history(customer_id: str, db: Session = Depends(get_db)):
    txs = db.query(Transaction).filter(Transaction.customer_id == customer_id).order_by(Transaction.timestamp.desc()).all()
    return [serialize_transaction(tx) for tx in txs]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db)):
    if not payload.customer_id or not payload.customer_id.strip():
        raise HTTPException(status_code=400, detail="Customer ID is required")
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")
    if not payload.location or not payload.location.strip():
        raise HTTPException(status_code=400, detail="Location is required")

    timestamp = payload.timestamp
    if timestamp.tzinfo is not None:
        timestamp = timestamp.astimezone(timezone.utc).replace(tzinfo=None)
    transaction = Transaction(
        customer_id=payload.customer_id.strip(),
        amount=float(payload.amount),
        timestamp=timestamp,
        location=payload.location.strip(),
        merchant=payload.merchant or "General Merchant",
        channel=payload.channel or "Web",
        status="pending",
        review_status_id=1,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    engine = FraudEngine()
    results, severity = engine.evaluate(db, transaction)
    notification_status = "not_applicable"
    if results:
        transaction.status = "flagged"
        transaction.review_status_id = 2
        db.commit()
        notification_service = AdminEmailNotificationService(db)
        notification = notification_service.send(
            title=f"High-risk {severity} alert",
            message=f"Transaction {transaction.id} for {transaction.customer_id} triggered {len(results)} rule(s).",
            severity=severity,
            transaction_id=transaction.id,
        )
        notification_status = "created" if notification else "failed"
    else:
        transaction.status = "clear"
        transaction.review_status_id = 1
        db.commit()

    db.refresh(transaction)
    return serialize_transaction(transaction, notification_status)


@router.patch("/{transaction_id}/review")
def update_review_status(transaction_id: int, payload: ReviewUpdate, db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    action = payload.action.lower()
    if action == "reviewed":
        tx.status = "reviewed"
        tx.review_status_id = 3
    elif action == "cleared":
        tx.status = "cleared"
        tx.review_status_id = 4
    else:
        raise HTTPException(status_code=400, detail="Action must be 'reviewed' or 'cleared'.")
    db.commit()
    db.refresh(tx)
    return serialize_transaction(tx)
