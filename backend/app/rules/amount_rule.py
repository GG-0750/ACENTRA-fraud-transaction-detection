from app.rules.base_rule import BaseRule, RuleResult


class AmountRule(BaseRule):
    rule_name = "Amount Rule"
    severity = "HIGH"

    def evaluate(self, transaction, context):
        history = context.get("customer_transactions", [])
        amounts = [item["amount"] for item in history if item["customer_id"] == transaction.customer_id and item["id"] != transaction.id]

        if not amounts:
            return RuleResult(
                triggered=False,
                rule_name=self.rule_name,
                severity=self.severity,
                reason="No historical customer amounts available for comparison.",
                evidence={"amount": transaction.amount, "history_count": 0},
            )

        avg_amount = sum(amounts) / len(amounts)
        median = sorted(amounts)[len(amounts) // 2]
        historical_max = max(amounts)
        multiplier = context.get("amount_multiplier", 3.0)
        threshold = max(avg_amount * multiplier, median * 4.0, historical_max * 2.5, 15000.0)
        triggered = transaction.amount > threshold

        if not triggered:
            return RuleResult(
                triggered=False,
                rule_name=self.rule_name,
                severity=self.severity,
                reason=f"Transaction amount ₹{transaction.amount:,.0f} is within the normal customer range.",
                evidence={"amount": float(transaction.amount), "average": avg_amount, "median": median, "historical_max": historical_max, "threshold": threshold, "multiplier": multiplier},
            )

        return RuleResult(
            triggered=True,
            rule_name=self.rule_name,
            severity="CRITICAL" if transaction.amount > threshold * 1.5 else self.severity,
            reason=f"Transaction amount ₹{transaction.amount:,.0f} is significantly higher than this customer's normal transaction range.",
            evidence={"amount": float(transaction.amount), "average": avg_amount, "median": median, "historical_max": historical_max, "threshold": threshold, "multiplier": multiplier},
        )
