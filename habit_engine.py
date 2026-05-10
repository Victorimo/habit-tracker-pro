"""
HabitEngine - Core logic for habit tracking.
Handles CRUD operations, streak calculations, completion tracking,
and weekly analytics. Data is persisted to a local JSON file.
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional


class HabitEngine:
    """Manages habit data, streaks, and analytics using local JSON storage."""

    def __init__(self, filepath: str = "data/habits.json"):
        self.filepath = filepath
        self._ensure_storage()
        self.data = self._load()

    def _ensure_storage(self):
        """Create storage directory and file if they don't exist."""
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        if not os.path.exists(self.filepath):
            self._save_raw({"habits": []})

    def _load(self) -> dict:
        """Load data from JSON file."""
        try:
            with open(self.filepath, "r") as f:
                data = json.load(f)
                if "habits" not in data:
                    data["habits"] = []
                return data
        except (json.JSONDecodeError, FileNotFoundError):
            return {"habits": []}

    def _save(self):
        """Persist current data to JSON file."""
        self._save_raw(self.data)

    def _save_raw(self, data: dict):
        """Write raw data dict to JSON file."""
        with open(self.filepath, "w") as f:
            json.dump(data, f, indent=2)

    def _find_habit(self, habit_id: str) -> Optional[dict]:
        """Find a habit by its ID."""
        for habit in self.data["habits"]:
            if habit["id"] == habit_id:
                return habit
        return None

    def create_habit(self, name: str, category: str = "General",
                     description: str = "", frequency: str = "daily") -> dict:
        """Create a new habit and persist it."""
        habit = {
            "id": str(uuid.uuid4())[:8],
            "name": name,
            "category": category,
            "description": description,
            "frequency": frequency,
            "completions": [],
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.data["habits"].append(habit)
        self._save()
        return habit

    def get_all_habits(self) -> list:
        """Return all habits."""
        return self.data["habits"]

    def get_habit(self, habit_id: str) -> Optional[dict]:
        """Return a single habit by ID."""
        return self._find_habit(habit_id)

    def update_habit(self, habit_id: str, updates: dict) -> Optional[dict]:
        """Update habit fields (name, category, description, frequency)."""
        habit = self._find_habit(habit_id)
        if habit is None:
            return None

        allowed_fields = {"name", "category", "description", "frequency"}
        for key, value in updates.items():
            if key in allowed_fields:
                habit[key] = value

        self._save()
        return habit

    def delete_habit(self, habit_id: str) -> bool:
        """Delete a habit by ID. Returns True if found and deleted."""
        habit = self._find_habit(habit_id)
        if habit is None:
            return False
        self.data["habits"].remove(habit)
        self._save()
        return True

    def mark_complete(self, habit_id: str, date_str: str) -> Optional[dict]:
        """Mark a habit as complete for a specific date."""
        habit = self._find_habit(habit_id)
        if habit is None:
            return None

        if date_str not in habit["completions"]:
            habit["completions"].append(date_str)
            habit["completions"].sort()
            self._save()

        return habit

    def unmark_complete(self, habit_id: str, date_str: str) -> Optional[dict]:
        """Remove a completion for a specific date."""
        habit = self._find_habit(habit_id)
        if habit is None:
            return None

        if date_str in habit["completions"]:
            habit["completions"].remove(date_str)
            self._save()

        return habit

    def calculate_streak(self, habit_id: str) -> int:
        """
        Calculate the current streak for a habit.
        
        A streak counts consecutive days of completion ending at today
        (or yesterday if today is not yet completed).
        
        For weekly habits, a streak counts consecutive weeks where the
        habit was completed at least once.
        """
        habit = self._find_habit(habit_id)
        if habit is None or not habit["completions"]:
            return 0

        if habit.get("frequency", "daily") == "weekly":
            return self._calculate_weekly_streak(habit)

        return self._calculate_daily_streak(habit)

    def _calculate_daily_streak(self, habit: dict) -> int:
        """Calculate consecutive daily completion streak."""
        completions = set(habit["completions"])
        today = datetime.now().date()

        # Start from today; if not completed today, try yesterday
        if today.strftime("%Y-%m-%d") in completions:
            check_date = today
        elif (today - timedelta(days=1)).strftime("%Y-%m-%d") in completions:
            check_date = today - timedelta(days=1)
        else:
            return 0

        streak = 0
        while check_date.strftime("%Y-%m-%d") in completions:
            streak += 1
            check_date -= timedelta(days=1)

        return streak

    def _calculate_weekly_streak(self, habit: dict) -> int:
        """Calculate consecutive weekly completion streak."""
        if not habit["completions"]:
            return 0

        completion_dates = sorted(
            [datetime.strptime(d, "%Y-%m-%d").date() for d in habit["completions"]],
            reverse=True,
        )

        # Get ISO week numbers for each completion
        completed_weeks = set()
        for d in completion_dates:
            iso = d.isocalendar()
            completed_weeks.add((iso[0], iso[1]))  # (year, week)

        today = datetime.now().date()
        current_iso = today.isocalendar()
        check_year, check_week = current_iso[0], current_iso[1]

        # Check if current or previous week is completed
        if (check_year, check_week) not in completed_weeks:
            check_week -= 1
            if check_week == 0:
                check_year -= 1
                check_week = datetime(check_year, 12, 28).isocalendar()[1]
            if (check_year, check_week) not in completed_weeks:
                return 0

        streak = 0
        while (check_year, check_week) in completed_weeks:
            streak += 1
            check_week -= 1
            if check_week == 0:
                check_year -= 1
                check_week = datetime(check_year, 12, 28).isocalendar()[1]

        return streak

    def calculate_longest_streak(self, habit_id: str) -> int:
        """Calculate the longest ever streak for a habit."""
        habit = self._find_habit(habit_id)
        if habit is None or not habit["completions"]:
            return 0

        completions = sorted(
            [datetime.strptime(d, "%Y-%m-%d").date() for d in habit["completions"]]
        )

        if not completions:
            return 0

        max_streak = 1
        current_streak = 1

        for i in range(1, len(completions)):
            if (completions[i] - completions[i - 1]).days == 1:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            elif (completions[i] - completions[i - 1]).days > 1:
                current_streak = 1

        return max_streak

    def calculate_completion_rate(self, habit_id: str, days: int = 30) -> float:
        """
        Calculate the completion rate over the last N days.
        Returns a float between 0.0 and 1.0.
        """
        habit = self._find_habit(habit_id)
        if habit is None:
            return 0.0

        today = datetime.now().date()
        created = datetime.strptime(habit["created_at"], "%Y-%m-%d %H:%M:%S").date()
        start_date = max(today - timedelta(days=days - 1), created)

        total_days = (today - start_date).days + 1
        if total_days <= 0:
            return 0.0

        completions = set(habit["completions"])
        completed_days = sum(
            1
            for i in range(total_days)
            if (start_date + timedelta(days=i)).strftime("%Y-%m-%d") in completions
        )

        return round(completed_days / total_days, 2)

    def get_weekly_analytics(self, days: int = 7) -> dict:
        """
        Generate analytics data for the dashboard.
        Returns daily completion counts and per-habit breakdowns.
        """
        today = datetime.now().date()
        date_range = [
            (today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days - 1, -1, -1)
        ]

        daily_totals = {d: 0 for d in date_range}
        habit_breakdowns = []

        for habit in self.data["habits"]:
            completions_in_range = [d for d in habit["completions"] if d in date_range]
            for d in completions_in_range:
                daily_totals[d] += 1

            habit_breakdowns.append({
                "id": habit["id"],
                "name": habit["name"],
                "category": habit["category"],
                "completions_in_period": len(completions_in_range),
                "total_possible": len(date_range),
                "rate": round(len(completions_in_range) / len(date_range), 2) if date_range else 0,
                "daily_data": [
                    {"date": d, "completed": d in habit["completions"]} for d in date_range
                ],
            })

        return {
            "period_days": days,
            "date_range": date_range,
            "daily_totals": [{"date": d, "count": daily_totals[d]} for d in date_range],
            "habits": habit_breakdowns,
            "overall_rate": round(
                sum(h["rate"] for h in habit_breakdowns) / len(habit_breakdowns), 2
            )
            if habit_breakdowns
            else 0,
        }
