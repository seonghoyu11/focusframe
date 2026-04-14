import os
from pymongo import MongoClient

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongodb:27017/appdb")
DB_NAME = "appdb"
COLLECTION_NAME = "ml_records"


def get_collection():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    return db[COLLECTION_NAME]


def save_record(record):
    collection = get_collection()
    collection.insert_one(record)