"""
User Profile Manager
Manages travel preferences, favourite destinations,
and recommendation history.
"""

import json
import os
import re
from typing import Dict, List
from datetime import datetime


class UserProfile:

    def __init__(self, user_id: str, profiles_dir: str = None):

        if not isinstance(user_id, str) or not re.fullmatch(
            r"[A-Za-z0-9_-]{1,50}", user_id
        ):
            raise ValueError("Invalid user ID.")

        self.user_id = user_id

        if profiles_dir is None:
            profiles_dir = os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "data",
                    "profiles"
                )
            )

        self.profiles_dir = profiles_dir
        os.makedirs(profiles_dir, exist_ok=True)

        self.profile_path = os.path.join(
            profiles_dir, f"{user_id}.json"
        )

        self.profile = self._load_or_create_profile()

    def _load_or_create_profile(self) -> Dict:

        if os.path.exists(self.profile_path):
            with open(self.profile_path, "r", encoding="utf-8") as f:
                profile = json.load(f)

            # Convert an existing study profile into a travel profile.
            if "learning_history" in profile:
                profile["preferences"] = self.default_preferences()
                profile["recommendation_history"] = []
                profile["favourites"] = []
                profile.pop("learning_history", None)
                profile.pop("completed_resources", None)
                profile.pop("bookmarks", None)
                self.profile = profile
                self.save()

            return profile

        return {
            "user_id": self.user_id,
            "created_at": datetime.now().isoformat(),
            "preferences": self.default_preferences(),
            "recommendation_history": [],
            "favourites": []
        }
# default travel preferences - new user 
    @staticmethod
    def default_preferences() -> Dict:
        return {
            "budget_rm": 500,
            "duration_days": 3,
            "destination_category": "Any",
            "activities": [],
            "travel_style": "budget",
            "companion": "friends",
            "region": "Any"
        }

    def set_preferences(self, preferences: Dict):
        """Save travel preferences."""
        self.profile["preferences"].update(preferences)
        self.save()

    def get_preferences(self) -> Dict:
        """Get saved travel preferences."""
        return self.profile.get("preferences", {})

    def add_to_recommendation_history(
        self, preferences: Dict, destination_ids: List[str]
    ):
        """Record recommendations generated for the user."""

        entry = {
            "preferences": preferences.copy(),
            "destination_ids": destination_ids,
            "timestamp": datetime.now().isoformat()
        }

        self.profile.setdefault(
            "recommendation_history", []
        ).append(entry)

        self.save()

    def get_recommendation_history(self, limit: int = 20) -> List[Dict]:
        """Get recent recommendation history."""
        history = self.profile.get("recommendation_history", [])
        return list(reversed(history[-limit:]))

    def add_favourite(self, destination_id: str):
        """Save a favourite destination."""

        favourites = self.profile.setdefault("favourites", [])

        if destination_id not in favourites:
            favourites.append(destination_id)
            self.save()

    def remove_favourite(self, destination_id: str):
        """Remove a favourite destination."""

        favourites = self.profile.setdefault("favourites", [])

        if destination_id in favourites:
            favourites.remove(destination_id)
            self.save()

    def get_favourites(self) -> List[str]:
        """Get saved destination IDs."""
        return self.profile.get("favourites", [])

    def save(self):
        """Save user profile to JSON."""

        with open(self.profile_path, "w", encoding="utf-8") as f:
            json.dump(self.profile, f, indent=4)

    def get_profile_summary(self) -> Dict:
        """Get user profile statistics."""

        return {
            "user_id": self.user_id,
            "preferences": self.get_preferences(),
            "total_recommendations": len(
                self.profile.get("recommendation_history", [])
            ),
            "total_favourites": len(self.get_favourites())
        }
