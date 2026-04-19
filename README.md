# FocusFrame

[![Web App CI](https://github.com/swe-students-spring2026/4-containers-terminal_titans/actions/workflows/web-app.yml/badge.svg)](https://github.com/swe-students-spring2026/4-containers-terminal_titans/actions/workflows/web-app.yml)
[![ML Client CI](https://github.com/swe-students-spring2026/4-containers-terminal_titans/actions/workflows/ml-client.yml/badge.svg)](https://github.com/swe-students-spring2026/4-containers-terminal_titans/actions/workflows/ml-client.yml)
[![Lint](https://github.com/swe-students-spring2026/4-containers-terminal_titans/actions/workflows/lint.yml/badge.svg)](https://github.com/swe-students-spring2026/4-containers-terminal_titans/actions/workflows/lint.yml)

This project is a containerized multiservice study-focus application. A user interacts with the Flask web application, the machine-learning client captures webcam frames and classifies them using facial emotion recognition, and session metadata plus snapshots are stored in MongoDB. A built-in Pomodoro timer and live distraction alerts run server-side, with the dashboard auto-refreshing every second while a session is active.

## Team

- [Prabhav Jalan](https://github.com/prabhavjalan)
- [Rehan Gupta](https://github.com/rehanguptaNYU)
- [Inoo Jung](https://github.com/ij2298-oss)
- [Caleb Jawharjian](https://github.com/calebjawharjian)
- [Steve](https://github.com/seonghoyu11)

## Task Board

- [**Project Task Board**](https://github.com/orgs/swe-students-spring2026/projects/90)

## Project Parts

1. `web-app/` — The Flask frontend and browser-facing routes. Handles user authentication, session start/stop controls, the Pomodoro timer, and the dashboard with server-side-rendered matplotlib charts.
2. `machine-learning-client/` — The background service that polls the database for active sessions, captures frames with OpenCV, classifies focus state using a local FER (facial expression recognition) model, and writes snapshots plus distraction notifications back to the database.
3. `mongodb` — The database container used by both services to store users (`users` collection), study sessions (`sessions` collection), and per-frame analysis results (`snapshots` collection).

## Prerequisites

- **Docker Desktop**
- **A webcam** accessible to the ML client container

## Setup

### 1. Clone the repository

```
git clone https://github.com/swe-students-spring2026/4-containers-terminal_titans.git
```

### 2. Configure environment variables

Copy the example environment file:

```
cp .env.example .env
```

Edit `.env` with your actual values — analysis is local, so no external API keys are required:

```
MONGO_URI=mongodb://mongodb:27017/
MONGO_DBNAME=focusframe
FLASK_SECRET_KEY=change-me-to-a-long-random-string
CAPTURE_INTERVAL_SECONDS=10
```

### 3. Initialize the database (first run only)

```
docker compose up -d mongodb
docker compose run --rm machine-learning-client python init_db.py
```

This creates the three collections and their indexes. The command is idempotent — rerunning it on an initialized database is safe.

### 4. Start all containers

Build and start the application:

```
docker compose up -d --build
```

The web application will be available at **http://localhost:3000**.

### 5. Stop the system

```
docker compose down
```

To also remove stored database data:

```
docker compose down -v
```

## Usage

1. Open **http://localhost:3000** in your browser.
2. Create an account or log in.
3. Click **Start Study Session** to begin. The dashboard will enter its active state, showing the Pomodoro timer and live stats, refreshing every second.
4. The background ML client will capture a frame every `CAPTURE_INTERVAL_SECONDS` seconds, classify your focus state, and store a snapshot.
5. If you appear distracted or step away, a banner will surface on the dashboard on the next refresh.
6. Click **Stop Session** to end. Your totals (focused / distracted / absent time) are computed from the snapshots and written back to the session record.
7. View past sessions under **History**, or drill into a single session to see the full snapshot timeline.

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `MONGO_URI` | MongoDB connection string | `mongodb://mongodb:27017/` |
| `MONGO_DBNAME` | MongoDB database name | `focusframe` |
| `FLASK_SECRET_KEY` | Flask session cookie signing key | `change-me` |
| `CAPTURE_INTERVAL_SECONDS` | Seconds between webcam captures; also the unit multiplier for stat aggregation | `10` |

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