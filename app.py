"""
Features: CRUD habits, mark as done, streak engine, weekly analytics.
"""

from flask import Flask, render_template, request, jsonify
from habit_engine import HabitEngine
from datetime import datetime

app = Flask(__name__)
engine = HabitEngine("data/habits.json")


@app.route("/")
def index():
    """Render the main dashboard."""
    return render_template("index.html")


@app.route("/api/habits", methods=["GET"])
def get_habits():
    """Return all habits with computed streaks and analytics."""
    habits = engine.get_all_habits()
    for habit in habits:
        habit["current_streak"] = engine.calculate_streak(habit["id"])
        habit["longest_streak"] = engine.calculate_longest_streak(habit["id"])
        habit["completion_rate"] = engine.calculate_completion_rate(habit["id"], days=30)
    return jsonify(habits)


@app.route("/api/habits", methods=["POST"])
def create_habit():
    """Create a new habit."""
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "Habit name is required"}), 400

    name = data["name"].strip()
    if len(name) == 0 or len(name) > 100:
        return jsonify({"error": "Habit name must be 1-100 characters"}), 400

    category = data.get("category", "General").strip()
    description = data.get("description", "").strip()
    frequency = data.get("frequency", "daily")

    if frequency not in ["daily", "weekly"]:
        return jsonify({"error": "Frequency must be 'daily' or 'weekly'"}), 400

    habit = engine.create_habit(name, category, description, frequency)
    return jsonify(habit), 201


@app.route("/api/habits/<habit_id>", methods=["PUT"])
def update_habit(habit_id):
    """Update an existing habit."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    habit = engine.update_habit(habit_id, data)
    if habit is None:
        return jsonify({"error": "Habit not found"}), 404
    return jsonify(habit)


@app.route("/api/habits/<habit_id>", methods=["DELETE"])
def delete_habit(habit_id):
    """Delete a habit."""
    success = engine.delete_habit(habit_id)
    if not success:
        return jsonify({"error": "Habit not found"}), 404
    return jsonify({"message": "Habit deleted"}), 200


@app.route("/api/habits/<habit_id>/complete", methods=["POST"])
def complete_habit(habit_id):
    """Mark a habit as completed for a given date."""
    data = request.get_json() or {}
    date_str = data.get("date", datetime.now().strftime("%Y-%m-%d"))

    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    result = engine.mark_complete(habit_id, date_str)
    if result is None:
        return jsonify({"error": "Habit not found"}), 404
    return jsonify(result)


@app.route("/api/habits/<habit_id>/uncomplete", methods=["POST"])
def uncomplete_habit(habit_id):
    """Unmark a habit completion for a given date."""
    data = request.get_json() or {}
    date_str = data.get("date", datetime.now().strftime("%Y-%m-%d"))

    result = engine.unmark_complete(habit_id, date_str)
    if result is None:
        return jsonify({"error": "Habit not found"}), 404
    return jsonify(result)


@app.route("/api/analytics", methods=["GET"])
def get_analytics():
    """Return weekly analytics data for all habits."""
    days = request.args.get("days", 7, type=int)
    if days < 1 or days > 90:
        days = 7
    analytics = engine.get_weekly_analytics(days)
    return jsonify(analytics)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
