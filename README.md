## Database Schema

**Database name:** `focusframe`

### Collection: `users`

Stores registered user accounts for the web app.

```json
{
  "_id": "ObjectId",
  "username": "string",
  "password_hash": "string",
  "created_at": "datetime"
}
```

**Indexes**
- unique index on `username`

---

### Collection: `sessions`

Stores study session metadata.

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "status": "active | completed",
  "start_time": "datetime",
  "end_time": "datetime | null",
  "pomodoro_phase": "work | break",
  "pomodoro_phase_start": "datetime",
  "pomodoro_cycle": "int",
  "total_focused_seconds": "int",
  "total_distracted_seconds": "int",
  "total_absent_seconds": "int",
  "snapshot_count": "int",
  "notification": {
    "type": "string",
    "message": "string",
    "timestamp": "datetime"
  }
}
```

**Indexes**
- index on `user_id`
- index on `status`

---

### Collection: `snapshots`

Stores each captured image and its analysis result.

```json
{
  "_id": "ObjectId",
  "session_id": "ObjectId",
  "user_id": "ObjectId",
  "timestamp": "datetime",
  "image_path": "string",
  "image_data": "base64 string",
  "emotion": {
    "dominant": "string | null",
    "confidence": "float",
    "all_emotions": "object"
  },
  "face_detected": "bool",
  "classification": "focused | distracted | absent"
}
```

**Indexes**
- index on `session_id`
- compound index on `user_id` + `timestamp`

---

## Environment Variables

Create a local `.env` file based on `.env.example`.

```env
MONGO_URI=mongodb+srv://USERNAME:PASSWORD@cluster0.xxxxx.mongodb.net/
MONGO_DBNAME=focusframe
CAPTURE_INTERVAL_SECONDS=30
FLASK_SECRET_KEY=replace_with_random_secret_key
```

**Notes**
- `.env` should not be committed to GitHub.
- `.env.example` should contain only dummy values.
- Both the ML client and the web app read MongoDB connection settings from environment variables.

---

## Database Initialization

The database can be initialized with the ML client container.

```bash
docker compose --env-file .env run --rm machine-learning-client python init_db.py
```

This creates the required collections and indexes:
- `users`
- `sessions`
- `snapshots`