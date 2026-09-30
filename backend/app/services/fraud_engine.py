from sqlalchemy.orm import Session

from app.models.fraud_flag import FraudFlag
from app.models.transaction import Transaction
from app.rules.registry import RuleRegistry


class FraudEngine:
    def __init__(self):
        self.registry = RuleRegistry()

    def build_context(self, db: Session, transaction: Transaction, overrides=None):
        history = []
        transactions = (
            db.query(Transaction)
            .filter(Transaction.customer_id == transaction.customer_id)
            .order_by(Transaction.timestamp.desc())
            .all()
        )
        for item in transactions:
            if item.id == transaction.id or item.timestamp > transaction.timestamp:
                continue
            history.append(
                {
                    "id": item.id,
                    "customer_id": item.customer_id,
                    "amount": float(item.amount),
                    "timestamp": item.timestamp,
                    "location": item.location,
                }
            )
        context = {
            "customer_transactions": history,
            "velocity_window_minutes": 30,
            "velocity_threshold": 4,
            "location_speed_threshold_kmh": 700.0,
            "amount_multiplier": 3.0,
        }
        if overrides:
            context.update(overrides)
        return context

    def determine_severity(self, results):
        rule_count = len(results)
        if rule_count >= 3 or any(result.severity == "CRITICAL" for result in results):
            return "CRITICAL"
        if rule_count >= 2 or any(result.severity == "HIGH" for result in results):
            return "HIGH"
        if rule_count:
            return "MEDIUM"
        return "LOW"

    def evaluate(self, db: Session, transaction: Transaction, overrides=None, persist=True, commit=True):
        context = self.build_context(db, transaction, overrides)
        results = []
        for rule in self.registry.get_rules():
            result = rule.evaluate(transaction, context)
            if result.triggered:
                results.append(result)
                if persist:
                    db.add(
                        FraudFlag(
                            transaction_id=transaction.id,
                            rule_name=result.rule_name,
                            severity=result.severity,
                            triggered=1,
                            reason=result.reason,
                            evidence=result.evidence,
                        )
                    )
        severity = self.determine_severity(results)
        if persist and commit:
            transaction.status = "flagged" if results else "clear"
            transaction.review_status_id = 2 if results else 1
            db.commit()
        elif persist:
            transaction.status = "flagged" if results else "clear"
            transaction.review_status_id = 2 if results else 1
            db.flush()
        return results, severity

    def analyze_rule_impact(self, db: Session):
        total = db.query(Transaction).count()
        flags = db.query(FraudFlag).all()
        rules_by_transaction = {}
        for flag in flags:
            rules_by_transaction.setdefault(flag.transaction_id, set()).add(flag.rule_name)
        velocity_count = sum("Velocity Rule" in rules for rules in rules_by_transaction.values())
        amount_count = sum("Amount Rule" in rules for rules in rules_by_transaction.values())
        location_count = sum("Location Rule" in rules for rules in rules_by_transaction.values())
        multi_rule_transactions = sum(1 for rules in rules_by_transaction.values() if len(rules) > 1)

        severity_breakdown = {
            "LOW": 0,
            "MEDIUM": 0,
            "HIGH": 0,
            "CRITICAL": 0,
        }
        for tx in db.query(Transaction).all():
            rules = rules_by_transaction.get(tx.id, set())
            if not rules:
                severity_breakdown["LOW"] += 1
                continue
            severities = {flag.severity for flag in tx.fraud_flags}
            if len(rules) >= 3 or "CRITICAL" in severities:
                severity_breakdown["CRITICAL"] += 1
            elif len(rules) >= 2 or "HIGH" in severities:
                severity_breakdown["HIGH"] += 1
            elif rules:
                severity_breakdown["MEDIUM"] += 1

        overlap = {
            "Velocity + Amount": sum({"Velocity Rule", "Amount Rule"}.issubset(rules) for rules in rules_by_transaction.values()),
            "Velocity + Location": sum({"Velocity Rule", "Location Rule"}.issubset(rules) for rules in rules_by_transaction.values()),
            "Amount + Location": sum({"Amount Rule", "Location Rule"}.issubset(rules) for rules in rules_by_transaction.values()),
            "All Three": sum({"Velocity Rule", "Amount Rule", "Location Rule"}.issubset(rules) for rules in rules_by_transaction.values()),
        }

        return {
            "total_transactions": total,
            "transactions_flagged": len({flag.transaction_id for flag in flags}),
            "velocity_rule_count": velocity_count,
            "amount_rule_count": amount_count,
            "location_rule_count": location_count,
            "multi_rule_transactions": multi_rule_transactions,
            "severity_breakdown": severity_breakdown,
            "rule_overlap": overlap,
        }

    def simulate_rule(self, db: Session, rule_name: str, threshold_count: int, window_minutes: int, amount_multiplier: float, speed_threshold_kmh: float):
        transactions = db.query(Transaction).order_by(Transaction.timestamp.asc()).all()
        affected = []
        existing_rule_transaction_ids = {
            flag.transaction_id
            for flag in db.query(FraudFlag).filter(FraudFlag.rule_name == rule_name).all()
        }
        existing_flagged_transaction_ids = {
            transaction_id
            for (transaction_id,) in db.query(FraudFlag.transaction_id).distinct().all()
        }
        overrides = {
            "velocity_threshold": threshold_count,
            "velocity_window_minutes": window_minutes,
            "amount_multiplier": amount_multiplier,
            "location_speed_threshold_kmh": speed_threshold_kmh,
        }
        for transaction in transactions:
            if rule_name not in {rule.rule_name for rule in self.registry.get_rules()}:
                raise ValueError(f"Unknown rule: {rule_name}")
            results, _ = self.evaluate(db, transaction, overrides=overrides, persist=False)
            if any(result.rule_name == rule_name for result in results):
                affected.append(transaction.id)
        newly_flagged = [transaction_id for transaction_id in affected if transaction_id not in existing_flagged_transaction_ids]
        newly_triggered_rule = [transaction_id for transaction_id in affected if transaction_id not in existing_rule_transaction_ids]
        return {
            "affected_transaction_ids": affected,
            "newly_flagged_transaction_ids": newly_flagged,
            "affected_count": len(affected),
            "new_flags_count": len(newly_flagged),
            "new_rule_triggers_count": len(newly_triggered_rule),
            "sample_transaction_ids": affected[:10],
            "rule_name": rule_name,
        }
