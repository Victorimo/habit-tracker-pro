"""
Unit Tests for HabitEngine - Core Logic Coverage.

Tests cover: CRUD operations, streak calculations (daily + weekly),
longest streak, completion rate, edge cases, and date handling.
"""

import json
import os
import pytest
from datetime import datetime, timedelta

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from habit_engine import HabitEngine


# ===== Fixtures =====

@pytest.fixture
def tmp_storage(tmp_path):
    """Provide a temporary JSON file path for each test."""
    return str(tmp_path / "test_habits.json")


@pytest.fixture
def engine(tmp_storage):
    """Provide a fresh HabitEngine instance."""
    return HabitEngine(tmp_storage)


@pytest.fixture
def engine_with_habits(engine):
    """Provide an engine pre-loaded with sample habits."""
    engine.create_habit("Exercise", "Fitness", "Morning jog", "daily")
    engine.create_habit("Read", "Learning", "30 minutes", "daily")
    engine.create_habit("Meditate", "Mindfulness", "", "daily")
    return engine


# ===== CRUD Tests =====

class TestCreateHabit:
    def test_create_basic_habit(self, engine):
        habit = engine.create_habit("Exercise")
        assert habit["name"] == "Exercise"
        assert habit["category"] == "General"
        assert habit["frequency"] == "daily"
        assert habit["completions"] == []
        assert "id" in habit
        assert "created_at" in habit

    def test_create_habit_with_all_fields(self, engine):
        habit = engine.create_habit("Read", "Learning", "30 min daily", "daily")
        assert habit["name"] == "Read"
        assert habit["category"] == "Learning"
        assert habit["description"] == "30 min daily"

    def test_create_weekly_habit(self, engine):
        habit = engine.create_habit("Laundry", "General", "", "weekly")
        assert habit["frequency"] == "weekly"

    def test_create_habit_persists_to_file(self, tmp_storage, engine):
        engine.create_habit("Test Habit")
        with open(tmp_storage) as f:
            data = json.load(f)
        assert len(data["habits"]) == 1
        assert data["habits"][0]["name"] == "Test Habit"

    def test_create_multiple_habits(self, engine):
        engine.create_habit("A")
        engine.create_habit("B")
        engine.create_habit("C")
        assert len(engine.get_all_habits()) == 3

    def test_unique_ids(self, engine):
        h1 = engine.create_habit("A")
        h2 = engine.create_habit("B")
        assert h1["id"] != h2["id"]


class TestReadHabit:
    def test_get_all_habits_empty(self, engine):
        assert engine.get_all_habits() == []

    def test_get_all_habits(self, engine_with_habits):
        habits = engine_with_habits.get_all_habits()
        assert len(habits) == 3

    def test_get_habit_by_id(self, engine):
        created = engine.create_habit("Test")
        found = engine.get_habit(created["id"])
        assert found["name"] == "Test"

    def test_get_nonexistent_habit(self, engine):
        assert engine.get_habit("nonexistent") is None


class TestUpdateHabit:
    def test_update_name(self, engine):
        habit = engine.create_habit("Old Name")
        updated = engine.update_habit(habit["id"], {"name": "New Name"})
        assert updated["name"] == "New Name"

    def test_update_category(self, engine):
        habit = engine.create_habit("Test", "General")
        updated = engine.update_habit(habit["id"], {"category": "Health"})
        assert updated["category"] == "Health"

    def test_update_nonexistent(self, engine):
        assert engine.update_habit("fake_id", {"name": "X"}) is None

    def test_update_ignores_invalid_fields(self, engine):
        habit = engine.create_habit("Test")
        engine.update_habit(habit["id"], {"id": "hacked", "completions": ["bad"]})
        refreshed = engine.get_habit(habit["id"])
        assert refreshed["id"] == habit["id"]  # ID unchanged
        assert refreshed["completions"] == []   # completions unchanged


class TestDeleteHabit:
    def test_delete_existing(self, engine):
        habit = engine.create_habit("Temp")
        assert engine.delete_habit(habit["id"]) is True
        assert engine.get_habit(habit["id"]) is None

    def test_delete_nonexistent(self, engine):
        assert engine.delete_habit("fake") is False

    def test_delete_persists(self, tmp_storage, engine):
        habit = engine.create_habit("Temp")
        engine.delete_habit(habit["id"])
        with open(tmp_storage) as f:
            data = json.load(f)
        assert len(data["habits"]) == 0


# ===== Completion Tests =====

class TestCompletions:
    def test_mark_complete(self, engine):
        habit = engine.create_habit("Test")
        result = engine.mark_complete(habit["id"], "2025-01-15")
        assert "2025-01-15" in result["completions"]

    def test_mark_complete_idempotent(self, engine):
        habit = engine.create_habit("Test")
        engine.mark_complete(habit["id"], "2025-01-15")
        engine.mark_complete(habit["id"], "2025-01-15")
        result = engine.get_habit(habit["id"])
        assert result["completions"].count("2025-01-15") == 1

    def test_mark_complete_nonexistent(self, engine):
        assert engine.mark_complete("fake", "2025-01-15") is None

    def test_unmark_complete(self, engine):
        habit = engine.create_habit("Test")
        engine.mark_complete(habit["id"], "2025-01-15")
        result = engine.unmark_complete(habit["id"], "2025-01-15")
        assert "2025-01-15" not in result["completions"]

    def test_unmark_nonexistent_date(self, engine):
        habit = engine.create_habit("Test")
        result = engine.unmark_complete(habit["id"], "2025-01-15")
        assert result is not None  # Should not error

    def test_completions_sorted(self, engine):
        habit = engine.create_habit("Test")
        engine.mark_complete(habit["id"], "2025-01-20")
        engine.mark_complete(habit["id"], "2025-01-10")
        engine.mark_complete(habit["id"], "2025-01-15")
        result = engine.get_habit(habit["id"])
        assert result["completions"] == ["2025-01-10", "2025-01-15", "2025-01-20"]


# ===== Streak Calculation Tests =====

class TestDailyStreak:
    def test_no_completions(self, engine):
        habit = engine.create_habit("Test")
        assert engine.calculate_streak(habit["id"]) == 0

    def test_streak_with_today(self, engine):
        habit = engine.create_habit("Test")
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        day_before = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")

        engine.mark_complete(habit["id"], day_before)
        engine.mark_complete(habit["id"], yesterday)
        engine.mark_complete(habit["id"], today)

        assert engine.calculate_streak(habit["id"]) == 3

    def test_streak_without_today(self, engine):
        """If today is not completed but yesterday is, streak still counts."""
        habit = engine.create_habit("Test")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        day_before = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")

        engine.mark_complete(habit["id"], day_before)
        engine.mark_complete(habit["id"], yesterday)

        assert engine.calculate_streak(habit["id"]) == 2

    def test_broken_streak(self, engine):
        """Gap in completions resets the streak."""
        habit = engine.create_habit("Test")
        today = datetime.now().strftime("%Y-%m-%d")
        three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")

        engine.mark_complete(habit["id"], three_days_ago)
        engine.mark_complete(habit["id"], today)

        assert engine.calculate_streak(habit["id"]) == 1

    def test_nonexistent_habit_streak(self, engine):
        assert engine.calculate_streak("fake") == 0

    def test_single_day_streak(self, engine):
        habit = engine.create_habit("Test")
        today = datetime.now().strftime("%Y-%m-%d")
        engine.mark_complete(habit["id"], today)
        assert engine.calculate_streak(habit["id"]) == 1

    def test_old_completions_no_streak(self, engine):
        """Completions from long ago don't count as current streak."""
        habit = engine.create_habit("Test")
        old_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        engine.mark_complete(habit["id"], old_date)
        assert engine.calculate_streak(habit["id"]) == 0


# ===== Longest Streak Tests =====

class TestLongestStreak:
    def test_no_completions(self, engine):
        habit = engine.create_habit("Test")
        assert engine.calculate_longest_streak(habit["id"]) == 0

    def test_single_completion(self, engine):
        habit = engine.create_habit("Test")
        engine.mark_complete(habit["id"], "2025-01-15")
        assert engine.calculate_longest_streak(habit["id"]) == 1

    def test_consecutive_days(self, engine):
        habit = engine.create_habit("Test")
        for i in range(5):
            d = (datetime(2025, 1, 10) + timedelta(days=i)).strftime("%Y-%m-%d")
            engine.mark_complete(habit["id"], d)
        assert engine.calculate_longest_streak(habit["id"]) == 5

    def test_broken_then_longer(self, engine):
        """Longest streak should find the longest segment."""
        habit = engine.create_habit("Test")
        # 3-day streak
        for i in range(3):
            engine.mark_complete(habit["id"], f"2025-01-{10+i:02d}")
        # Gap, then 5-day streak
        for i in range(5):
            engine.mark_complete(habit["id"], f"2025-01-{20+i:02d}")

        assert engine.calculate_longest_streak(habit["id"]) == 5

    def test_nonexistent_habit(self, engine):
        assert engine.calculate_longest_streak("fake") == 0


# ===== Completion Rate Tests =====

class TestCompletionRate:
    def test_no_completions(self, engine):
        habit = engine.create_habit("Test")
        assert engine.calculate_completion_rate(habit["id"]) == 0.0

    def test_full_completion(self, engine):
        habit = engine.create_habit("Test")
        today = datetime.now()
        for i in range(30):
            d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            engine.mark_complete(habit["id"], d)
        assert engine.calculate_completion_rate(habit["id"], 30) == 1.0

    def test_partial_completion(self, engine):
        habit = engine.create_habit("Test")
        today = datetime.now()
        # Complete every other day for 10 days
        for i in range(0, 10, 2):
            d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            engine.mark_complete(habit["id"], d)
        rate = engine.calculate_completion_rate(habit["id"], 10)
        assert 0.0 < rate < 1.0

    def test_nonexistent_habit(self, engine):
        assert engine.calculate_completion_rate("fake") == 0.0


# ===== Analytics Tests =====

class TestWeeklyAnalytics:
    def test_empty_analytics(self, engine):
        analytics = engine.get_weekly_analytics(7)
        assert analytics["period_days"] == 7
        assert len(analytics["date_range"]) == 7
        assert analytics["overall_rate"] == 0
        assert analytics["habits"] == []

    def test_analytics_with_data(self, engine):
        habit = engine.create_habit("Test")
        today = datetime.now().strftime("%Y-%m-%d")
        engine.mark_complete(habit["id"], today)

        analytics = engine.get_weekly_analytics(7)
        assert len(analytics["habits"]) == 1
        assert analytics["habits"][0]["completions_in_period"] >= 1

    def test_analytics_date_range(self, engine):
        analytics = engine.get_weekly_analytics(7)
        dates = analytics["date_range"]
        assert len(dates) == 7
        # Dates should be in ascending order
        assert dates == sorted(dates)

    def test_analytics_daily_totals(self, engine):
        h1 = engine.create_habit("A")
        h2 = engine.create_habit("B")
        today = datetime.now().strftime("%Y-%m-%d")
        engine.mark_complete(h1["id"], today)
        engine.mark_complete(h2["id"], today)

        analytics = engine.get_weekly_analytics(7)
        today_total = next(d for d in analytics["daily_totals"] if d["date"] == today)
        assert today_total["count"] == 2


# ===== Data Persistence Tests =====

class TestPersistence:
    def test_data_survives_reload(self, tmp_storage):
        engine1 = HabitEngine(tmp_storage)
        habit = engine1.create_habit("Persist Me")
        engine1.mark_complete(habit["id"], "2025-01-15")

        # Create new engine instance (simulates app restart)
        engine2 = HabitEngine(tmp_storage)
        habits = engine2.get_all_habits()
        assert len(habits) == 1
        assert habits[0]["name"] == "Persist Me"
        assert "2025-01-15" in habits[0]["completions"]

    def test_corrupted_file_recovery(self, tmp_storage):
        """Engine should recover gracefully from corrupted JSON."""
        with open(tmp_storage, "w") as f:
            f.write("NOT VALID JSON!!!")

        engine = HabitEngine(tmp_storage)
        assert engine.get_all_habits() == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
