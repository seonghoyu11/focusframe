"""MongoDB helper functions for the machine-learning client."""

import os
from pymongo import MongoClient  # pylint: disable=import-error

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongodb:27017/focusframe")
DB_NAME = "focusframe"

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


# Maintain backward compatibility with name 'save_record' if needed
def save_record(record):
    """Alias for save_snapshot."""
    return save_snapshot(record)
