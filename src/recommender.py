"""
Study Resource Recommender Engine
Provides rule-based recommendations for study resources based on user preferences.
"""

import json
import os
from typing import List, Dict, Tuple


class StudyRecommender:
    """
    Rule-based recommendation system for study resources.
    
    The recommender uses a scoring system based on:
    - Subject matching (40% weight)
    - Difficulty level progression (30% weight)
    - Format preference (20% weight)
    - Tag matching (10% weight)
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize the recommender with resources and rules.
        
        Args:
            data_dir: Path to directory containing resources.json and rules.json
        """
        self.data_dir = data_dir
        self.resources = []
        self.rules = {}
        self.load_data()
    
    def load_data(self):
        """Load resources and rules from JSON files."""
        # Load resources
        resources_path = os.path.join(self.data_dir, "resources.json")
        if os.path.exists(resources_path):
            with open(resources_path, 'r') as f:
                self.resources = json.load(f)
        else:
            raise FileNotFoundError(f"Resources file not found: {resources_path}")
        
        # Load rules
        rules_path = os.path.join(self.data_dir, "rules.json")
        if os.path.exists(rules_path):
            with open(rules_path, 'r') as f:
                self.rules = json.load(f)
        else:
            raise FileNotFoundError(f"Rules file not found: {rules_path}")
    
    def recommend(self, user_preferences: Dict) -> List[Tuple[Dict, float]]:
        """
        Generate recommendations based on user preferences.
        
        Args:
            user_preferences: Dictionary containing:
                - subject: str (e.g., "programming", "mathematics")
                - difficulty: str (e.g., "beginner", "intermediate", "advanced")
                - format: str (e.g., "video", "text", "mixed")
                - tags: list of str (optional, e.g., ["python", "ai"])
                - exclude_ids: list of str (optional, resource IDs to exclude)
        
        Returns:
            List of tuples (resource, score) sorted by score (highest first)
        """
        recommendations = []
        exclude_ids = user_preferences.get("exclude_ids", [])
        
        for resource in self.resources:
            # Skip excluded resources
            if resource["id"] in exclude_ids:
                continue
            
            # Calculate score
            score = self._calculate_score(resource, user_preferences)
            
            # Only include if above threshold
            if score >= self.rules.get("minimum_score_threshold", 0):
                recommendations.append((resource, score))
        
        # Sort by score (highest first)
        recommendations.sort(key=lambda x: x[1], reverse=True)
        
        return recommendations
    
    def _calculate_score(self, resource: Dict, user_preferences: Dict) -> float:
        """
        Calculate recommendation score for a resource.
        
        Args:
            resource: Resource dictionary
            user_preferences: User preferences dictionary
        
        Returns:
            Score between 0 and 100
        """
        score = 0
        weights = self.rules.get("weights", {})
        
        # Subject match (40%)
        subject_weight = weights.get("subject_match", 40)
        if resource["subject"] == user_preferences.get("subject"):
            score += subject_weight
        
        # Difficulty match (30%)
        difficulty_weight = weights.get("difficulty_match", 30)
        user_difficulty = user_preferences.get("difficulty", "beginner")
        allowed_difficulties = self.rules.get("difficulty_progression", {}).get(
            user_difficulty, [user_difficulty]
        )
        if resource["difficulty"] in allowed_difficulties:
            score += difficulty_weight
        
        # Format preference (20%)
        format_weight = weights.get("format_preference", 20)
        user_format = user_preferences.get("format", "mixed")
        if user_format == "mixed" or resource["format"] == user_format:
            score += format_weight
        
        # Tag matching (10%)
        tag_weight = weights.get("tag_match", 10)
        user_tags = set(user_preferences.get("tags", []))
        resource_tags = set(resource.get("tags", []))
        if user_tags and resource_tags:
            tag_overlap = len(user_tags & resource_tags)
            tag_score = (tag_overlap / len(user_tags)) * tag_weight
            score += tag_score
        
        return score
    
    def get_resource_by_id(self, resource_id: str) -> Dict:
        """
        Get a resource by its ID.
        
        Args:
            resource_id: The resource ID
        
        Returns:
            Resource dictionary or None if not found
        """
        for resource in self.resources:
            if resource["id"] == resource_id:
                return resource
        return None
    
    def get_all_subjects(self) -> List[str]:
        """Get list of all available subjects."""
        subjects = set()
        for resource in self.resources:
            subjects.add(resource["subject"])
        return sorted(list(subjects))
    
    def get_all_formats(self) -> List[str]:
        """Get list of all available formats."""
        formats = set()
        for resource in self.resources:
            formats.add(resource["format"])
        return sorted(list(formats))
    
    def get_resources_by_subject(self, subject: str) -> List[Dict]:
        """Get all resources for a specific subject."""
        return [r for r in self.resources if r["subject"] == subject]
    
    def add_resource(self, resource: Dict) -> bool:
        """
        Add a new resource to the system.
        
        Args:
            resource: Resource dictionary with required fields
        
        Returns:
            True if successful, False otherwise
        """
        required_fields = ["id", "title", "type", "subject", "difficulty", "format"]
        if not all(field in resource for field in required_fields):
            return False
        
        # Check for duplicate ID
        if self.get_resource_by_id(resource["id"]):
            return False
        
        self.resources.append(resource)
        return True
    
    def save_resources(self):
        """Save current resources to JSON file."""
        resources_path = os.path.join(self.data_dir, "resources.json")
        with open(resources_path, 'w') as f:
            json.dump(self.resources, f, indent=4)
    
    def get_stats(self) -> Dict:
        """Get statistics about the resource collection."""
        stats = {
            "total_resources": len(self.resources),
            "by_type": {},
            "by_subject": {},
            "by_difficulty": {}
        }
        
        for resource in self.resources:
            # Count by type
            res_type = resource.get("type", "unknown")
            stats["by_type"][res_type] = stats["by_type"].get(res_type, 0) + 1
            
            # Count by subject
            subject = resource.get("subject", "unknown")
            stats["by_subject"][subject] = stats["by_subject"].get(subject, 0) + 1
            
            # Count by difficulty
            difficulty = resource.get("difficulty", "unknown")
            stats["by_difficulty"][difficulty] = stats["by_difficulty"].get(difficulty, 0) + 1
        
        return stats
