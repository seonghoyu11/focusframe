# FocusFrame

[![Web App CI](https://github.com/swe-students-spring2026/4-containers-terminal_titans/actions/workflows/web-app.yml/badge.svg)](https://github.com/swe-students-spring2026/4-containers-terminal_titans/actions/workflows/web-app.yml)
[![ML Client CI](https://github.com/swe-students-spring2026/4-containers-terminal_titans/actions/workflows/ml-client.yml/badge.svg)](https://github.com/swe-students-spring2026/4-containers-terminal_titans/actions/workflows/ml-client.yml)
[![Lint](https://github.com/swe-students-spring2026/4-containers-terminal_titans/actions/workflows/lint.yml/badge.svg)](https://github.com/swe-students-spring2026/4-containers-terminal_titans/actions/workflows/lint.yml)

FocusFrame is a containerized multi-service study-focus application. While a study session is running, the user's browser captures webcam frames every few seconds and posts them to the Flask web app. A separate machine-learning client polls MongoDB for unanalyzed frames, runs facial-expression recognition on each, and writes the focused/distracted classification back. The dashboard shows a live video preview, a Pomodoro timer, running per-session stats, and a distraction banner that fires whenever the user looks away or shows a non-neutral expression.

## Team

- [Prabhav Jalan](https://github.com/prabhavjalan)
- [Rehan Gupta](https://github.com/rehanguptaNYU)
- [Inoo Jung](https://github.com/ij2298-oss)
- [Caleb Jawharjian](https://github.com/calebjawharjian)
- [Steve Yoo](https://github.com/seonghoyu11)

## Task Board

- [**Project Task Board**](https://github.com/orgs/swe-students-spring2026/projects/90)

## Project Parts

1. `web-app/` — Flask frontend. Handles auth, session start/stop controls, the Pomodoro timer, receives browser frame uploads, exposes a JSON state endpoint for live polling, and renders the history + session detail views with server-side matplotlib charts.
2. `machine-learning-client/` — Background analysis worker. Polls MongoDB for unanalyzed snapshots, runs FER, writes classifications back, and sets per-session distraction notifications.
3. `mongodb` — Local database container used by both services.

## Prerequisites

- **Docker Desktop**
- **A webcam** in the machine running the browser (the container does not need webcam access)
- **A modern browser** (Chrome, Firefox, Safari, or Edge) for `getUserMedia` support

## Setup

### 1. Clone the repository

```
git clone https://github.com/swe-students-spring2026/4-containers-terminal_titans.git
```

### 2. Configure environment variables

Copy the example environment file and edit as needed:

```
cp .env.example .env
```

At minimum, set `FLASK_SECRET_KEY` to a long random string. Everything else has sensible defaults.

```
MONGO_URI=mongodb://mongodb:27017/
MONGO_DBNAME=focusframe
FLASK_SECRET_KEY=change-me-to-a-long-random-string
CAPTURE_INTERVAL_SECONDS=10
ANALYSIS_INTERVAL_SECONDS=3
```

### 3. Build and start all containers

```
docker compose up -d --build
```

First-time builds take 10–20 minutes because of TensorFlow. Subsequent rebuilds use cached layers and take seconds.

The web app will be available at **http://localhost:3000**.

### 4. Initialize the database (first run only)

```
docker compose exec machine-learning-client python init_db.py
docker compose exec mongodb mongosh focusframe --quiet --eval "db.snapshots.createIndex({analyzed: 1})"
```

Both commands are idempotent — safe to rerun.

### 5. Stop the system

```
docker compose down
```

To also wipe all stored users, sessions, and snapshots:

```
docker compose down -v
```

## Usage

1. Open **http://localhost:3000**.
2. Create an account or log in.
3. Click **Start Study Session**. The browser will prompt for camera permission — allow it.
4. A live preview of your webcam appears on the dashboard. Every `CAPTURE_INTERVAL_SECONDS`, the browser silently captures a JPEG and uploads it to the web app.
5. The ML client analyzes each frame within a few seconds and writes the classification back. The stats card updates in real time.
6. If you look away or change expression away from neutral, a distraction banner appears. It clears automatically after ~30 seconds without further distraction.
7. Click **Stop Session** to end. Per-session totals are computed from the snapshots and written back to the session record.
8. Visit **History** to see past sessions, or click into a single session for the full snapshot timeline.

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `MONGO_URI` | MongoDB connection string | `mongodb://mongodb:27017/` |
| `MONGO_DBNAME` | MongoDB database name | `focusframe` |
| `FLASK_SECRET_KEY` | Flask session cookie signing key | (no default; set in `.env`) |
| `CAPTURE_INTERVAL_SECONDS` | How often the browser captures and uploads a frame | `10` |
| `ANALYSIS_INTERVAL_SECONDS` | How often the ML client polls for unanalyzed frames | `3` |


## Running Tests

The project uses `pipenv` for dependency management. Ensure it is installed before running tests.

### ML Client

```
cd machine-learning-client
pipenv install --dev
pipenv run pytest tests/ -v
```

### Web App

```
cd web-app
pipenv install --dev
pipenv run pytest tests/ -v --cov=.
```

The web-app CI workflow gates merges at ≥80% coverage.
