"""Rule-based Malaysian travel destination recommendation engine.

Worksheet modifications:
1. Strict budget filtering: never recommend a destination above the user's budget.
2. Activity and destination-category matching, with input validation.

Budget estimates are indicative per person and exclude transport to the destination.
"""

import json
import math
from pathlib import Path


class TravelRecommender:
    # Category labels are mapped to existing destination activities/travel styles.
    # This avoids inventing new categories in the destination dataset.
    CATEGORY_RULES = {
        "beach": {"activities": {"beach"}},
        "nature": {"activities": {"nature", "wildlife", "hiking"}, "styles": {"nature"}},
        "city": {"styles": {"city"}},
        "historical": {"activities": {"history"}},
        "adventure": {"activities": {"adventure", "hiking", "diving", "island_hopping"}, "styles": {"adventure"}},
        "culture": {"activities": {"culture", "history"}, "styles": {"culture"}},
        "food": {"activities": {"food"}},
        "shopping": {"activities": {"shopping"}},
        "theme_parks": {"activities": {"theme_parks"}},
    }

    def __init__(self, data_dir=None):
        # Works when run from the project folder or imported by Flask.
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).resolve().parent.parent / "data"
        self.destinations = self._read_json("destinations.json")
        self.rules = self._read_json("travel_rules.json")
        # Festival promotions are demo-only, stored separately from destination prices.
        festival_file = self.data_dir / "festival_promotions.json"
        festival_data = self._read_json("festival_promotions.json") if festival_file.is_file() else {"festivals": []}
        self.festivals = {f["id"]: f for f in festival_data.get("festivals", [])}
        self.form_options = self._read_json("malaysia_travel_form_options.json") if (
            self.data_dir / "malaysia_travel_form_options.json"
        ).is_file() else {}

    def _read_json(self, filename):
        with (self.data_dir / filename).open("r", encoding="utf-8") as file:
            return json.load(file)

    @staticmethod
    def _normalise(value):
        return str(value).strip().lower().replace(" ", "_").replace("-", "_")

    def _parse_preferences(self, preferences):
        if not isinstance(preferences, dict):
            raise ValueError("Travel preferences must be provided as a dictionary.")

        try:
            budget = float(preferences.get("budget_rm"))
        except (TypeError, ValueError, OverflowError):
            raise ValueError("Enter a valid numeric budget in RM.") from None
        if not math.isfinite(budget) or budget <= 0:
            raise ValueError("Enter a budget greater than RM0.")

        raw_days = preferences.get("duration_days")
        try:
            days_number = float(raw_days)
        except (TypeError, ValueError, OverflowError):
            raise ValueError("Enter a valid whole number of travel days.") from None
        if not math.isfinite(days_number) or not days_number.is_integer():
            raise ValueError("Travel duration must be a whole number of days.")
        days = int(days_number)
        max_days = self.form_options.get("duration_days", {}).get("max", 14)
        if not 1 <= days <= max_days:
            raise ValueError(f"Travel duration must be between 1 and {max_days} days.")

        raw_activities = preferences.get("activities", [])
        if not isinstance(raw_activities, (list, tuple, set)):
            raise ValueError("Select activities from the available activity options.")
        activities = {self._normalise(item) for item in raw_activities}
        allowed_activities = set(self.form_options.get("activities", []))
        if allowed_activities and not activities.issubset(allowed_activities):
            raise ValueError("One or more selected activities are not available.")

        category = self._normalise(preferences.get("destination_category") or preferences.get("category") or "any")
        if category not in ("any", "") and category not in self.CATEGORY_RULES:
            raise ValueError("Choose a valid destination category (e.g. Beach, Nature, City, Historical).")

        style = self._normalise(preferences.get("travel_style", "any"))
        companion = self._normalise(preferences.get("companion", "any"))
        region = self._normalise(preferences.get("region", "any"))
        for field, value, options in (
            ("travel style", style, self.form_options.get("travel_styles", [])),
            ("companion", companion, self.form_options.get("companions", [])),
            ("region", region, self.form_options.get("regions", [])),
        ):
            if options and value not in ("any", "") and value not in {self._normalise(x) for x in options}:
                raise ValueError(f"Choose a valid {field}.")

        exclude_ids = preferences.get("exclude_ids", [])
        if not isinstance(exclude_ids, (list, tuple, set)):
            raise ValueError("Excluded destination IDs must be a list.")

        return budget, days, activities, category, style, companion, region, set(exclude_ids)

    def _matches_category(self, destination, category):
        if category in ("any", ""):
            return True
        rules = self.CATEGORY_RULES[category]
        activities = {self._normalise(x) for x in destination.get("activities", [])}
        styles = {self._normalise(x) for x in destination.get("travel_styles", [])}
        return bool(activities & rules.get("activities", set()) or styles & rules.get("styles", set()))

    def recommend(self, preferences, festival_id=None):
        """Return ranked, within-budget results with explanations."""
        weights = self.rules["weights"]
        threshold = self.rules.get("minimum_score_threshold", 35)
        limit = self.rules.get("maximum_recommendations", 10)
        days_tolerance = self.rules.get("duration_tolerance_days", 1)
        budget, days, activities, category, style, companion, region, exclude_ids = self._parse_preferences(preferences)

        if festival_id is not None and festival_id not in self.festivals:
            raise ValueError("Choose a valid festival.")
        festival = self.festivals.get(festival_id, {})
        offers = festival.get("offers", {})

        results = []
        for destination in self.destinations:
            if destination["id"] in exclude_ids:
                continue
            if region not in ("any", "") and self._normalise(destination["region"]) != region:
                continue
            if not self._matches_category(destination, category):
                continue

            min_days = destination["recommended_days_min"]
            max_days = destination["recommended_days_max"]
            # Price the FULL selected trip, not a clamped 2-3-day stay.
            # A longer stay can still be suggested, with a suitability warning.
            planned_days = days
            original_cost = round(destination["estimated_daily_budget_rm"] * planned_days, 2)
            discount_percent = float(offers.get(destination["id"], 0))
            if not 0 <= discount_percent <= 70:
                discount_percent = 0
            estimated_cost = round(original_cost * (1 - discount_percent / 100), 2)

            # Modification 1: STRICT budget filtering, as promised in worksheet Section 7.
            if estimated_cost > budget:
                continue

            score = float(weights["budget_match"])
            reasons = ["Fits your estimated travel budget"]
            if discount_percent:
                reasons.append(f"{festival['name']} offer: {discount_percent:g}% off")
            warnings = []
            if category not in ("any", ""):
                reasons.append("Matches destination category: " + category.replace("_", " "))

            # Modification 2: activity-based weighted matching.
            available = {self._normalise(a) for a in destination.get("activities", [])}
            matched = activities & available
            if activities:
                score += weights["activity_match"] * len(matched) / len(activities)
                if matched:
                    reasons.append("Matches activities: " + ", ".join(sorted(matched)))
            else:
                score += weights["activity_match"]  # No activity preference.

            if min_days <= days <= max_days:
                score += weights["duration_match"]
                reasons.append("Suitable for your available travel days")
            elif days < min_days:
                if min_days - days <= days_tolerance:
                    score += weights["duration_match"] * 0.5
                warnings.append(f"Usually recommended for {min_days}–{max_days} days; your trip is {days} day(s)")
            elif days > max_days:
                if days - max_days <= days_tolerance:
                    score += weights["duration_match"] * 0.5
                warnings.append(f"Usually recommended for {min_days}–{max_days} days; your trip is {days} day(s)")

            styles = {self._normalise(s) for s in destination.get("travel_styles", [])}
            if style in ("any", "") or style in styles:
                score += weights["travel_style_match"]
                if style not in ("any", ""):
                    reasons.append("Matches your travel style")

            companions = {self._normalise(c) for c in destination.get("suitable_for", [])}
            if companion in ("any", "") or companion in companions:
                score += weights["companion_match"]
                if companion not in ("any", ""):
                    reasons.append("Suitable for your travel companion")

            if score >= threshold:
                results.append({
                    "destination": destination,
                    "score": round(score, 1),
                    "estimated_total_rm": estimated_cost,
                    "original_total_rm": original_cost,
                    "discount_percent": discount_percent,
                    "festival_name": festival.get("name", "") if discount_percent else "",
                    "suggested_days": planned_days,
                    "reasons": reasons,
                    "warnings": warnings,
                })

        results.sort(key=lambda item: (-item["score"], item["estimated_total_rm"]))
        return results[:limit]


if __name__ == "__main__":
    engine = TravelRecommender()
    sample_preferences = {
        "budget_rm": 800,
        "duration_days": 3,
        "destination_category": "Historical",
        "activities": ["food", "history"],
        "travel_style": "culture",
        "companion": "friends",
        "region": "any",
    }
    recommendations = engine.recommend(sample_preferences)
    if not recommendations:
        print("No matching destinations found. Try adjusting your preferences.")
    for result in recommendations:
        print(f'{result["destination"]["name"]}: {result["score"]}/100 '
              f'(estimated RM{result["estimated_total_rm"]})')
        print("  Reasons:", "; ".join(result["reasons"]) or "Partial match")
        if result["warnings"]:
            print("  Note:", "; ".join(result["warnings"]))
