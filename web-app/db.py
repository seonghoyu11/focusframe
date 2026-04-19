"""MongoDB helper functions for the web app."""

import os
from pymongo import MongoClient  # pylint: disable=import-error

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongodb:27017/")
DB_NAME = os.environ.get("MONGO_DBNAME", "focusframe")

USERS_COLLECTION = "users"
SESSIONS_COLLECTION = "sessions"
SNAPSHOTS_COLLECTION = "snapshots"


def get_database():
    """Return the MongoDB database used by the web app."""
    client = MongoClient(MONGO_URI)
    return client[DB_NAME]


def get_collection(name):
    """Return a specific MongoDB collection."""
    return get_database()[name]


def get_users_collection():
    """Return the users collection."""
    return get_collection(USERS_COLLECTION)


def save_snapshot(snapshot_data):
    """Insert one analysis snapshot into the snapshots collection."""
    collection = get_collection(SNAPSHOTS_COLLECTION)
    return collection.insert_one(snapshot_data)