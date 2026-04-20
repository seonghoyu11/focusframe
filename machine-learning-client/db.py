"""MongoDB helper functions for the FocusFrame ML client."""

import datetime
import os

from pymongo import MongoClient  # pylint: disable=import-error

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongodb:27017/focusframe")
DB_NAME = os.environ.get("MONGO_DBNAME", "focusframe")

# Collection Names
USERS_COLLECTION = "users"
SESSIONS_COLLECTION = "sessions"
SNAPSHOTS_COLLECTION = "snapshots"


def get_collection(name):
    """Return a specific MongoDB collection."""
    client = MongoClient(MONGO_URI)
    database = client[DB_NAME]
    return database[name]


def save_snapshot(snapshot_data):
    """Insert one analysis snapshot into the snapshots collection."""
    collection = get_collection(SNAPSHOTS_COLLECTION)
    return collection.insert_one(snapshot_data)


def save_record(record):
    """Alias for save_snapshot (backward compatibility)."""
    return save_snapshot(record)


def set_session_notification(session_id, classification):
    """Set the notification field on a session document."""
    if classification != "distracted":
        return

    sessions = get_collection(SESSIONS_COLLECTION)
    sessions.update_one(
        {"_id": session_id},
        {
            "$set": {
                "notification": {
                    "type": "distracted",
                    "message": "You seem distracted! Refocus on your work.",
                    "timestamp": datetime.datetime.now(datetime.timezone.utc),
                }
            }
        },
    )
