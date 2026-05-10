# Habit Tracker Pro

A local web application for tracking daily habits, calculating streaks, and visualising weekly analytics.

Built as part of COMP8066 — AI-Powered Mini SDLC Project.

## Features

- **CRUD Habits** — Create, read, update, and delete habits with categories and frequency settings.
- **Daily Completion Tracking** — Mark habits as done/undone for any date.
- **Streak Engine** — Calculates current streak, longest streak, and 30-day completion rate.
- **Weekly Analytics** — Interactive charts (bar chart + doughnut) showing completion trends over 7/14/30 days.
- **Local JSON Storage** — All data persisted to `data/habits.json`, no database required.

## Tech Stack

- **Back-end**: Python 3.10+, Flask 3.0
- **Front-end**: HTML5, CSS3, Vanilla JavaScript
- **Charts**: Chart.js 4.4
- **Storage**: Local JSON file
- **Testing**: pytest

## Quick Start

### Prerequisites
- Python 3.10 or higher
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/habit-tracker-pro.git
cd habit-tracker-pro

# Create and activate a virtual environment (recommended)
python -m venv venv
source venv/bin/activate    # On macOS/Linux
venv\Scripts\activate       # On Windows

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
python app.py
```

Open your browser and navigate to `http://localhost:5000`.

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run only unit tests
pytest tests/test_habit_engine.py -v

# Run only integration tests
pytest tests/test_integration.py -v
```

## Project Structure

```
habit-tracker-pro/
├── app.py                  # Flask application (routes & API)
├── habit_engine.py         # Core logic (streaks, analytics, storage)
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── data/
│   └── habits.json         # Local data storage (auto-created)
├── static/
│   ├── css/
│   │   └── style.css       # Application styles
│   └── js/
│       └── app.js          # Frontend JavaScript
├── templates/
│   └── index.html          # Main HTML template
└── tests/
    ├── test_habit_engine.py  # Unit tests (35+ tests)
    └── test_integration.py   # Integration tests (11 tests)
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/habits` | List all habits with streaks |
| POST | `/api/habits` | Create a new habit |
| PUT | `/api/habits/<id>` | Update a habit |
| DELETE | `/api/habits/<id>` | Delete a habit |
| POST | `/api/habits/<id>/complete` | Mark habit complete |
| POST | `/api/habits/<id>/uncomplete` | Unmark habit completion |
| GET | `/api/analytics?days=7` | Get analytics data |

## Non-Trivial Feature: Streak Engine

The streak engine calculates consecutive days of habit completion. It handles:

- **Current streak**: Counts back from today (or yesterday if today isn't completed yet).
- **Weekly frequency**: Counts consecutive weeks with at least one completion.
- **Longest streak**: Finds the longest consecutive completion sequence in history.
- **Completion rate**: Percentage of days completed over a configurable window.

## Licence

This project was created for academic purposes (COMP8066).
