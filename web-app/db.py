"""MongoDB helper functions for the web app."""

import os
from pymongo import MongoClient  # pylint: disable=import-error

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongodb:27017/appdb")
DB_NAME = "appdb"
COLLECTION_NAME = "ml_records"


def get_collection():
    """Return the MongoDB collection used by the web app."""
    client = MongoClient(MONGO_URI)
    database = client[DB_NAME]
    return database[COLLECTION_NAME]


def get_recent_records(limit=10):
    """Return the most recent records from MongoDB."""
    collection = get_collection()
    return list(collection.find().sort("timestamp", -1).limit(limit))