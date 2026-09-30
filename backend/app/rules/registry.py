from app.rules.amount_rule import AmountRule
from app.rules.location_rule import LocationRule
from app.rules.velocity_rule import VelocityRule


class RuleRegistry:
    def __init__(self):
        self.rules = [VelocityRule(), AmountRule(), LocationRule()]

    def get_rules(self):
        return self.rules
