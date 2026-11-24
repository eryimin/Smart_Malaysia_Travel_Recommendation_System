"""
Command-Line Interface for Study Resource Recommender
Provides an interactive menu-driven interface for users.
"""

import sys
import os
from recommender import StudyRecommender
from user_profile import UserProfile


class RecommenderCLI:
    """Interactive CLI for the study resource recommender."""
    
    def __init__(self):
        """Initialize the CLI."""
        self.recommender = StudyRecommender()
        self.current_user = None
        self.running = True
    
    def run(self):
        """Start the CLI application."""
        print("\n" + "="*60)
        print("Welcome to Study Resource Recommender")
        print("="*60 + "\n")
        
        while self.running:
            if not self.current_user:
                self._show_main_menu()
            else:
                self._show_user_menu()
    
    def _show_main_menu(self):
        """Display main menu."""
        print("\nMain Menu:")
        print("1. Load/Create User Profile")
        print("2. Browse All Resources")
        print("3. View System Statistics")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            self._load_user_profile()
        elif choice == "2":
            self._browse_resources()
        elif choice == "3":
            self._show_statistics()
        elif choice == "4":
            self.running = False
            print("\nGoodbye!")
        else:
            print("Invalid choice. Please try again.")
    
    def _show_user_menu(self):
        """Display user menu."""
        user_summary = self.current_user.get_profile_summary()
        print(f"\n--- User: {user_summary['user_id']} ---")
        print("1. Get Recommendations")
        print("2. Update Preferences")
        print("3. View My Bookmarks")
        print("4. View Learning History")
        print("5. Browse All Resources")
        print("6. Switch User")
        print("7. Exit")
        
        choice = input("\nEnter your choice (1-7): ").strip()
        
        if choice == "1":
            self._get_recommendations()
        elif choice == "2":
            self._update_preferences()
        elif choice == "3":
            self._view_bookmarks()
        elif choice == "4":
            self._view_learning_history()
        elif choice == "5":
            self._browse_resources()
        elif choice == "6":
            self.current_user = None
        elif choice == "7":
            self.running = False
            print("\nGoodbye!")
        else:
            print("Invalid choice. Please try again.")
    
    def _load_user_profile(self):
        """Load or create a user profile."""
        user_id = input("Enter your user ID (or press Enter for 'student1'): ").strip()
        if not user_id:
            user_id = "student1"
        
        try:
            self.current_user = UserProfile(user_id)
            print(f"\nLoaded profile for user: {user_id}")
        except Exception as e:
            print(f"Error loading profile: {e}")
    
    def _get_recommendations(self):
        """Get personalized recommendations."""
        if not self.current_user:
            print("Please load a user profile first.")
            return
        
        preferences = self.current_user.get_preferences()
        
        # Add exclude list
        completed = self.current_user.get_completed_resources()
        preferences["exclude_ids"] = completed
        
        recommendations = self.recommender.recommend(preferences)
        
        if not recommendations:
            print("\nNo recommendations found. Try adjusting your preferences.")
            return
        
        print(f"\n{'='*60}")
        print(f"Recommendations for {self.current_user.user_id}")
        print(f"{'='*60}")
        print(f"Based on: {preferences['subject']} ({preferences['difficulty']})")
        print(f"Format: {preferences['format']}\n")
        
        for idx, (resource, score) in enumerate(recommendations, 1):
            print(f"{idx}. {resource['title']}")
            print(f"   Type: {resource['type']} | Subject: {resource['subject']}")
            print(f"   Difficulty: {resource['difficulty']} | Duration: {resource['duration_hours']}h")
            print(f"   Score: {score:.1f}/100")
            print(f"   Tags: {', '.join(resource.get('tags', []))}")
            print()
        
        # Allow user to interact with recommendations
        self._interact_with_recommendations(recommendations)
    
    def _interact_with_recommendations(self, recommendations):
        """Allow user to bookmark or mark resources as viewed."""
        while True:
            choice = input("Enter resource number to bookmark (or 'q' to go back): ").strip()
            
            if choice.lower() == 'q':
                break
            
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(recommendations):
                    resource = recommendations[idx][0]
                    self.current_user.bookmark_resource(resource["id"])
                    self.current_user.add_to_learning_history(resource["id"], "viewed")
                    print(f"✓ Bookmarked: {resource['title']}")
                else:
                    print("Invalid number. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a number or 'q'.")
    
    def _update_preferences(self):
        """Update user preferences."""
        if not self.current_user:
            print("Please load a user profile first.")
            return
        
        print("\n--- Update Preferences ---")
        print(f"Available subjects: {', '.join(self.recommender.get_all_subjects())}")
        
        subject = input("Enter subject (or press Enter to keep current): ").strip()
        
        print(f"Available difficulties: beginner, intermediate, advanced")
        difficulty = input("Enter difficulty (or press Enter to keep current): ").strip()
        
        print(f"Available formats: {', '.join(self.recommender.get_all_formats())}, mixed")
        format_pref = input("Enter format preference (or press Enter to keep current): ").strip()
        
        tags_input = input("Enter tags separated by commas (or press Enter to keep current): ").strip()
        
        # Build update dictionary
        updates = {}
        if subject:
            updates["subject"] = subject
        if difficulty:
            updates["difficulty"] = difficulty
        if format_pref:
            updates["format"] = format_pref
        if tags_input:
            updates["tags"] = [tag.strip() for tag in tags_input.split(",")]
        
        if updates:
            self.current_user.set_preferences(updates)
            print("\n✓ Preferences updated!")
        else:
            print("\nNo changes made.")
    
    def _view_bookmarks(self):
        """View bookmarked resources."""
        if not self.current_user:
            print("Please load a user profile first.")
            return
        
        bookmarks = self.current_user.get_bookmarks()
        
        if not bookmarks:
            print("\nYou have no bookmarks yet.")
            return
        
        print(f"\n{'='*60}")
        print("Your Bookmarks")
        print(f"{'='*60}\n")
        
        for idx, resource_id in enumerate(bookmarks, 1):
            resource = self.recommender.get_resource_by_id(resource_id)
            if resource:
                print(f"{idx}. {resource['title']}")
                print(f"   Type: {resource['type']} | Subject: {resource['subject']}")
                print(f"   URL: {resource.get('url', 'N/A')}")
                print()
    
    def _view_learning_history(self):
        """View user's learning history."""
        if not self.current_user:
            print("Please load a user profile first.")
            return
        
        history = self.current_user.get_learning_history(limit=10)
        
        if not history:
            print("\nYour learning history is empty.")
            return
        
        print(f"\n{'='*60}")
        print("Recent Learning History (Last 10 entries)")
        print(f"{'='*60}\n")
        
        for idx, entry in enumerate(history, 1):
            resource = self.recommender.get_resource_by_id(entry["resource_id"])
            resource_title = resource["title"] if resource else "Unknown Resource"
            print(f"{idx}. {resource_title}")
            print(f"   Action: {entry['action']} | Time: {entry['timestamp']}")
            print()
    
    def _browse_resources(self):
        """Browse all available resources."""
        print(f"\n{'='*60}")
        print("All Available Resources")
        print(f"{'='*60}\n")
        
        for idx, resource in enumerate(self.recommender.resources, 1):
            print(f"{idx}. {resource['title']}")
            print(f"   Type: {resource['type']} | Subject: {resource['subject']}")
            print(f"   Difficulty: {resource['difficulty']} | Duration: {resource['duration_hours']}h")
            print()
    
    def _show_statistics(self):
        """Show system statistics."""
        stats = self.recommender.get_stats()
        
        print(f"\n{'='*60}")
        print("System Statistics")
        print(f"{'='*60}\n")
        
        print(f"Total Resources: {stats['total_resources']}\n")
        
        print("By Type:")
        for res_type, count in stats['by_type'].items():
            print(f"  {res_type}: {count}")
        
        print("\nBy Subject:")
        for subject, count in stats['by_subject'].items():
            print(f"  {subject}: {count}")
        
        print("\nBy Difficulty:")
        for difficulty, count in stats['by_difficulty'].items():
            print(f"  {difficulty}: {count}")


def main():
    """Main entry point."""
    cli = RecommenderCLI()
    try:
        cli.run()
    except KeyboardInterrupt:
        print("\n\nApplication interrupted. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
