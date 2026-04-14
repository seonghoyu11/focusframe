"""MongoDB helper functions for the machine-learning client."""

import os
from pymongo import MongoClient  # pylint: disable=import-error

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongodb:27017/appdb")
DB_NAME = "appdb"
COLLECTION_NAME = "ml_records"


def get_collection():
    """Return the MongoDB collection used by the ML client."""
    client = MongoClient(MONGO_URI)
    database = client[DB_NAME]
    return database[COLLECTION_NAME]


def save_record(record):
    """Insert one analysis record into MongoDB."""
    collection = get_collection()
    collection.insert_one(record)
