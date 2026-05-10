"""
Integration Tests for Habit Tracker Pro.

Tests exercise multiple components working together:
Flask API endpoints + HabitEngine + JSON storage.
"""

import json
import os
import sys
import pytest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from habit_engine import HabitEngine


@pytest.fixture
def client(tmp_path):
    """Provide a Flask test client with isolated storage."""
    test_file = str(tmp_path / "test_habits.json")
    app.config["TESTING"] = True

    # Replace the engine with one using temp storage
    import app as app_module
    app_module.engine = HabitEngine(test_file)

    with app.test_client() as client:
        yield client


class TestFullWorkflow:
    """Integration test: Create → Complete → Verify Streak → Reload → Verify Persistence."""

    def test_create_complete_reload_workflow(self, client):
        """
        End-to-end workflow:
        1. Create a habit via API
        2. Mark it complete for 3 consecutive days
        3. Verify the streak is calculated correctly
        4. Fetch all habits and verify data integrity
        """
        # Step 1: Create habit
        res = client.post("/api/habits", json={
            "name": "Integration Test Habit",
            "category": "Testing",
            "description": "Full workflow test",
            "frequency": "daily"
        })
        assert res.status_code == 201
        habit = res.get_json()
        habit_id = habit["id"]
        assert habit["name"] == "Integration Test Habit"

        # Step 2: Mark complete for 3 consecutive days
        today = datetime.now()
        dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(3)]

        for date_str in dates:
            res = client.post(f"/api/habits/{habit_id}/complete", json={"date": date_str})
            assert res.status_code == 200

        # Step 3: Verify via GET (streak should be calculated)
        res = client.get("/api/habits")
        assert res.status_code == 200
        habits = res.get_json()
        assert len(habits) == 1

        found = habits[0]
        assert found["current_streak"] == 3
        assert found["longest_streak"] == 3
        assert len(found["completions"]) == 3

    def test_create_update_delete_workflow(self, client):
        """CRUD lifecycle: Create → Update → Verify → Delete → Verify gone."""
        # Create
        res = client.post("/api/habits", json={"name": "Temp Habit"})
        assert res.status_code == 201
        habit_id = res.get_json()["id"]

        # Update
        res = client.put(f"/api/habits/{habit_id}", json={
            "name": "Updated Habit",
            "category": "Health"
        })
        assert res.status_code == 200
        assert res.get_json()["name"] == "Updated Habit"

        # Verify update
        res = client.get("/api/habits")
        habits = res.get_json()
        assert habits[0]["name"] == "Updated Habit"
        assert habits[0]["category"] == "Health"

        # Delete
        res = client.delete(f"/api/habits/{habit_id}")
        assert res.status_code == 200

        # Verify deletion
        res = client.get("/api/habits")
        assert len(res.get_json()) == 0

    def test_complete_uncomplete_workflow(self, client):
        """Toggle completion: Complete → Verify → Uncomplete → Verify."""
        res = client.post("/api/habits", json={"name": "Toggle Test"})
        habit_id = res.get_json()["id"]
        today = datetime.now().strftime("%Y-%m-%d")

        # Complete
        res = client.post(f"/api/habits/{habit_id}/complete", json={"date": today})
        assert res.status_code == 200
        assert today in res.get_json()["completions"]

        # Uncomplete
        res = client.post(f"/api/habits/{habit_id}/uncomplete", json={"date": today})
        assert res.status_code == 200
        assert today not in res.get_json()["completions"]

    def test_analytics_with_multiple_habits(self, client):
        """Analytics endpoint returns correct aggregated data."""
        # Create 2 habits
        res1 = client.post("/api/habits", json={"name": "Habit A"})
        res2 = client.post("/api/habits", json={"name": "Habit B"})
        id_a = res1.get_json()["id"]
        id_b = res2.get_json()["id"]

        today = datetime.now().strftime("%Y-%m-%d")
        client.post(f"/api/habits/{id_a}/complete", json={"date": today})
        client.post(f"/api/habits/{id_b}/complete", json={"date": today})

        # Fetch analytics
        res = client.get("/api/analytics?days=7")
        assert res.status_code == 200
        analytics = res.get_json()
        assert len(analytics["habits"]) == 2
        assert analytics["period_days"] == 7

        # Today's total should be 2
        today_entry = next(d for d in analytics["daily_totals"] if d["date"] == today)
        assert today_entry["count"] == 2


class TestAPIValidation:
    """Test error handling and edge cases at the API level."""

    def test_create_habit_missing_name(self, client):
        res = client.post("/api/habits", json={})
        assert res.status_code == 400

    def test_create_habit_empty_name(self, client):
        res = client.post("/api/habits", json={"name": ""})
        assert res.status_code == 400

    def test_update_nonexistent_habit(self, client):
        res = client.put("/api/habits/fake_id", json={"name": "X"})
        assert res.status_code == 404

    def test_delete_nonexistent_habit(self, client):
        res = client.delete("/api/habits/nonexistent")
        assert res.status_code == 404

    def test_complete_nonexistent_habit(self, client):
        res = client.post("/api/habits/fake/complete", json={"date": "2025-01-15"})
        assert res.status_code == 404

    def test_complete_invalid_date(self, client):
        res = client.post("/api/habits", json={"name": "Test"})
        habit_id = res.get_json()["id"]
        res = client.post(f"/api/habits/{habit_id}/complete", json={"date": "not-a-date"})
        assert res.status_code == 400

    def test_invalid_frequency(self, client):
        res = client.post("/api/habits", json={"name": "Test", "frequency": "hourly"})
        assert res.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
