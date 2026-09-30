from datetime import timedelta

from app.rules.base_rule import BaseRule, RuleResult


class VelocityRule(BaseRule):
    rule_name = "Velocity Rule"
    severity = "HIGH"

    def evaluate(self, transaction, context):
        customer_id = transaction.customer_id
        window_minutes = context.get("velocity_window_minutes", 30)
        threshold = context.get("velocity_threshold", 4)
        history = context.get("customer_transactions", [])

        recent = []
        for item in history:
            if item["customer_id"] != customer_id:
                continue
            if item["id"] == transaction.id:
                continue
            delta = transaction.timestamp - item["timestamp"]
            if timedelta(0) <= delta <= timedelta(minutes=window_minutes):
                recent.append(item)

        count = len(recent) + 1
        triggered = count > threshold

        if not triggered:
            return RuleResult(
                triggered=False,
                rule_name=self.rule_name,
                severity=self.severity,
                reason=f"Customer {customer_id} made {count} transactions within {window_minutes} minutes; below threshold.",
                evidence={**self._evidence(count, window_minutes, threshold, recent)},
            )

        return RuleResult(
            triggered=True,
            rule_name=self.rule_name,
            severity="CRITICAL" if count >= threshold + 2 else self.severity,
            reason=f"Customer {customer_id} made {count} transactions within {window_minutes} minutes.",
            evidence=self._evidence(count, window_minutes, threshold, recent),
        )

    @staticmethod
    def _evidence(count, window_minutes, threshold, recent):
        return {
            "count": count,
            "window_minutes": window_minutes,
            "threshold": threshold,
            "transactions": [
                {**item, "timestamp": item["timestamp"].isoformat()}
                for item in recent
            ],
        }
