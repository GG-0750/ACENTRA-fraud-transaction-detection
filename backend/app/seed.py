from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from sqlalchemy import inspect

from app.core.database import Base, SessionLocal, engine
from app.models.database_migration import DatabaseMigration
from app.models.fraud_flag import FraudFlag
from app.models.notification import Notification
from app.models.review_status import ReviewStatus
from app.models.transaction import Transaction
from app.services.demo_notification import DemoNotificationService
from app.services.fraud_engine import FraudEngine


def initialize_database():
    Base.metadata.create_all(bind=engine)
    migrate_notification_email_columns()
    db = SessionLocal()
    try:
        status_rows = [
            {"id": 1, "name": "pending", "description": "Awaiting review"},
            {"id": 2, "name": "flagged", "description": "Flagged for investigation"},
            {"id": 3, "name": "reviewed", "description": "Reviewed by a fraud analyst"},
            {"id": 4, "name": "cleared", "description": "Cleared after investigation"},
        ]
        for row in status_rows:
            if not db.query(ReviewStatus).filter(ReviewStatus.id == row["id"]).first():
                db.add(ReviewStatus(**row))
        db.commit()

        repair_legacy_seed_results(db)
        if db.query(Transaction).count() == 0:
            seed_demo_data(db)
        db.commit()
    finally:
        db.close()


def migrate_notification_email_columns():
    columns = {column["name"] for column in inspect(engine).get_columns("notifications")}
    with engine.begin() as connection:
        if "email_status" not in columns:
            connection.exec_driver_sql("ALTER TABLE notifications ADD COLUMN email_status VARCHAR(30) NOT NULL DEFAULT 'not_required'")
        if "email_recipient" not in columns:
            connection.exec_driver_sql("ALTER TABLE notifications ADD COLUMN email_recipient VARCHAR(254)")


def repair_legacy_seed_results(db: Session):
    """Rebuild existing fraud results once using the registered rule engine."""
    migration_id = "rebuild_fraud_flags_with_registered_rules_v1"
    if db.query(DatabaseMigration).filter(DatabaseMigration.id == migration_id).first():
        return

    review_decisions = {
        tx.id: (tx.status, tx.review_status_id)
        for tx in db.query(Transaction).all()
        if tx.status in {"reviewed", "cleared"}
    }
    db.query(FraudFlag).delete(synchronize_session=False)
    db.query(Notification).filter(Notification.title == "High-risk detection").delete(synchronize_session=False)
    existing_notification_transactions = {
        transaction_id
        for (transaction_id,) in db.query(Notification.transaction_id).filter(Notification.transaction_id.isnot(None)).all()
    }
    db.flush()
    db.expire_all()

    fraud_engine = FraudEngine()
    notification_service = DemoNotificationService(db)
    transactions = db.query(Transaction).order_by(Transaction.timestamp.asc(), Transaction.id.asc()).all()
    pending_notifications = []
    for tx in transactions:
        results, severity = fraud_engine.evaluate(db, tx, commit=False)
        if tx.id in review_decisions:
            tx.status, tx.review_status_id = review_decisions[tx.id]
        if results and severity in {"HIGH", "CRITICAL"} and tx.id not in existing_notification_transactions:
            pending_notifications.append((tx, severity, len(results)))
    for tx, severity, rule_count in pending_notifications:
        db.add(Notification(
            title=f"High-risk {severity} alert",
            message=f"Transaction {tx.id} for {tx.customer_id} triggered {rule_count} registered rule(s).",
            severity=severity,
            transaction_id=tx.id,
            is_demo=True,
        ))
    db.add(DatabaseMigration(id=migration_id))
    db.commit()


def seed_demo_data(db: Session):
    start = datetime(2025, 1, 15, 9, 0, 0)
    customers = ["C101", "C102", "C103", "C104", "C105", "C106", "C107", "C108", "C109", "C110"]
    normal_locations = ["Chennai", "Mumbai", "Bengaluru", "Delhi", "Hyderabad", "Pune", "Kolkata", "Ahmedabad"]

    normal_transactions = []
    for idx in range(1, 181):
        customer_id = customers[(idx - 1) % len(customers)]
        location = normal_locations[(idx * 3) % len(normal_locations)]
        minutes_offset = idx * 11
        amount = 900 + ((idx * 137) % 4200)
        transaction = Transaction(
            customer_id=customer_id,
            amount=float(amount),
            timestamp=start + timedelta(minutes=minutes_offset),
            location=location,
            merchant=f"Merchant {idx % 20}",
            channel="Web" if idx % 2 == 0 else "App",
            status="clear",
            review_status_id=1,
        )
        normal_transactions.append(transaction)

    special_cases = [
        Transaction(customer_id="C102", amount=2000.0, timestamp=start + timedelta(hours=10, minutes=20), location="Chennai", merchant="Hotel Bookings", channel="App", status="clear", review_status_id=1),
        Transaction(customer_id="C102", amount=3000.0, timestamp=start + timedelta(hours=10, minutes=25), location="Chennai", merchant="Travel", channel="App", status="clear", review_status_id=1),
        Transaction(customer_id="C102", amount=4500.0, timestamp=start + timedelta(hours=10, minutes=31), location="Chennai", merchant="Dining", channel="Web", status="clear", review_status_id=1),
        Transaction(customer_id="C102", amount=7000.0, timestamp=start + timedelta(hours=10, minutes=38), location="Chennai", merchant="Retail", channel="App", status="clear", review_status_id=1),
        Transaction(customer_id="C102", amount=48500.0, timestamp=start + timedelta(hours=10, minutes=42), location="Mumbai", merchant="Luxury Goods", channel="Web", status="clear", review_status_id=1),

        Transaction(customer_id="C203", amount=580.0, timestamp=start + timedelta(days=1, hours=9, minutes=10), location="Bengaluru", merchant="Groceries", channel="App", status="clear", review_status_id=1),
        Transaction(customer_id="C203", amount=1400.0, timestamp=start + timedelta(days=1, hours=9, minutes=15), location="Bengaluru", merchant="Transport", channel="App", status="clear", review_status_id=1),
        Transaction(customer_id="C203", amount=3500.0, timestamp=start + timedelta(days=1, hours=9, minutes=18), location="Bengaluru", merchant="Electronics", channel="Web", status="clear", review_status_id=1),
        Transaction(customer_id="C203", amount=6700.0, timestamp=start + timedelta(days=1, hours=9, minutes=23), location="Bengaluru", merchant="Home", channel="Web", status="clear", review_status_id=1),
        Transaction(customer_id="C203", amount=8000.0, timestamp=start + timedelta(days=1, hours=9, minutes=28), location="Bengaluru", merchant="Travel", channel="App", status="clear", review_status_id=1),

        Transaction(customer_id="C301", amount=2200.0, timestamp=start + timedelta(days=2, hours=8, minutes=12), location="Chennai", merchant="Recharge", channel="App", status="clear", review_status_id=1),
        Transaction(customer_id="C301", amount=3100.0, timestamp=start + timedelta(days=2, hours=8, minutes=18), location="Chennai", merchant="Food", channel="App", status="clear", review_status_id=1),
        Transaction(customer_id="C301", amount=5200.0, timestamp=start + timedelta(days=2, hours=8, minutes=27), location="Mumbai", merchant="Aviation", channel="Web", status="clear", review_status_id=1),

        Transaction(customer_id="C401", amount=4750.0, timestamp=start + timedelta(days=3, hours=15, minutes=5), location="Delhi", merchant="Bills", channel="App", status="clear", review_status_id=1),
        Transaction(customer_id="C401", amount=18500.0, timestamp=start + timedelta(days=3, hours=15, minutes=13), location="Delhi", merchant="Gold", channel="Web", status="clear", review_status_id=1),
    ]

    for tx in normal_transactions + special_cases:
        db.add(tx)
    db.commit()

    db.commit()
    engine = FraudEngine()
    notification_service = DemoNotificationService(db)
    for tx in db.query(Transaction).order_by(Transaction.timestamp.asc(), Transaction.id.asc()).all():
        results, severity = engine.evaluate(db, tx)
        if results and severity in {"HIGH", "CRITICAL"}:
            notification_service.send(
                title=f"High-risk {severity} alert",
                message=f"Transaction {tx.id} for {tx.customer_id} triggered {len(results)} registered rule(s).",
                severity=severity,
                transaction_id=tx.id,
            )
