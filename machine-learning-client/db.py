"""MongoDB helper functions for the FocusFrame ML client."""

import os
import datetime
from pymongo import MongoClient  # pylint: disable=import-error

MONGO_URI = os.environ["MONGO_URI"]
DB_NAME = os.environ.get("MONGO_DBNAME", "focusframe")

SESSIONS_COLLECTION = "sessions"
SNAPSHOTS_COLLECTION = "snapshots"


def get_database():
    """Return the MongoDB database used by the ML client."""
    client = MongoClient(MONGO_URI)
    return client[DB_NAME]


def get_active_session():
    """Return one active session, or None if no active session exists."""
    database = get_database()
    return database[SESSIONS_COLLECTION].find_one({"status": "active"})


def save_snapshot(snapshot):
    """Insert one snapshot analysis record into MongoDB."""
    database = get_database()
    database[SNAPSHOTS_COLLECTION].insert_one(snapshot)


def update_session_notification(session_id, notification_type, message):
    """Update the active session with a distraction/absence notification."""
    database = get_database()
    database[SESSIONS_COLLECTION].update_one(
        {"_id": session_id},
        {
            "$set": {
                "notification": {
                    "type": notification_type,
                    "message": message,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc),
                }
            }
        },
    )