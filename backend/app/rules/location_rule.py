from datetime import timedelta

from app.rules.base_rule import BaseRule, RuleResult

CITY_COORDS = {
    "chennai": (13.0827, 80.2707),
    "mumbai": (19.0760, 72.8777),
    "bengaluru": (12.9716, 77.5946),
    "delhi": (28.6139, 77.2090),
    "hyderabad": (17.3850, 78.4867),
    "pune": (18.5204, 73.8567),
    "kolkata": (22.5726, 88.3639),
    "ahmedabad": (23.0225, 72.5714),
    "coimbatore": (11.0168, 76.9558),
}


def haversine_km(lat1, lon1, lat2, lon2):
    import math

    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class LocationRule(BaseRule):
    rule_name = "Location Rule"
    severity = "HIGH"

    def evaluate(self, transaction, context):
        history = context.get("customer_transactions", [])
        previous = None
        recent = []
        for item in history:
            if item["customer_id"] == transaction.customer_id and item["id"] != transaction.id:
                recent.append(item)
        if recent:
            previous = max(recent, key=lambda x: x["timestamp"])

        if previous is None:
            return RuleResult(
                triggered=False,
                rule_name=self.rule_name,
                severity=self.severity,
                reason="No prior transaction exists for location comparison.",
                evidence={"current_location": transaction.location},
            )

        prev_city = str(previous["location"]).strip().lower()
        curr_city = str(transaction.location).strip().lower()
        prev_coords = CITY_COORDS.get(prev_city)
        curr_coords = CITY_COORDS.get(curr_city)

        if prev_coords is None or curr_coords is None:
            return RuleResult(
                triggered=False,
                rule_name=self.rule_name,
                severity=self.severity,
                reason="Location comparison is unavailable because one or both cities are not mapped.",
                evidence={"previous_location": previous["location"], "current_location": transaction.location},
            )

        time_diff_minutes = max(1, (transaction.timestamp - previous["timestamp"]).total_seconds() / 60)
        distance_km = haversine_km(prev_coords[0], prev_coords[1], curr_coords[0], curr_coords[1])
        speed_kmh = distance_km / (time_diff_minutes / 60)
        threshold_kmh = context.get("location_speed_threshold_kmh", 700.0)
        triggered = speed_kmh > threshold_kmh

        if not triggered:
            return RuleResult(
                triggered=False,
                rule_name=self.rule_name,
                severity=self.severity,
                reason=f"Travel speed from {previous['location']} to {transaction.location} is plausible at {speed_kmh:,.1f} km/h.",
                evidence={"previous_location": previous["location"], "current_location": transaction.location, "time_difference_minutes": time_diff_minutes, "distance_km": round(distance_km, 1), "speed_kmh": round(speed_kmh, 1)},
            )

        return RuleResult(
            triggered=True,
            rule_name=self.rule_name,
            severity="CRITICAL" if speed_kmh > threshold_kmh * 1.5 else self.severity,
            reason=f"Previous transaction was in {previous['location']} at {previous['timestamp']}; current transaction is in {transaction.location} {time_diff_minutes:.0f} minutes later, requiring an implausible travel speed.",
            evidence={"previous_location": previous["location"], "current_location": transaction.location, "time_difference_minutes": round(time_diff_minutes, 1), "distance_km": round(distance_km, 1), "speed_kmh": round(speed_kmh, 1)},
        )
