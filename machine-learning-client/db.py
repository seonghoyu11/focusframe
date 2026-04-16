"""MongoDB helper functions for the student study tracking ML client."""

import os
from pymongo import MongoClient  # pylint: disable=import-error

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongodb:27017/appdb")
DB_NAME = "appdb"
COLLECTION_NAME = "ml_records"


def get_collection():
    """Return the MongoDB collection used to store study tracking records."""
    client = MongoClient(MONGO_URI)
    database = client[DB_NAME]
    return database[COLLECTION_NAME]


def save_record(record):
    """Insert one study tracking analysis record into MongoDB."""
    collection = get_collection()
    collection.insert_one(record)
