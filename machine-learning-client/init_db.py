"""Initialize the FocusFrame MongoDB database with collections and indexes."""

import os
from pymongo import MongoClient  # pylint: disable=import-error

MONGO_URI = os.environ["MONGO_URI"]
DB_NAME = os.environ.get("MONGO_DBNAME", "focusframe")


def main():
    """Create required collections and indexes."""
    client = MongoClient(MONGO_URI)
    database = client[DB_NAME]

    existing = database.list_collection_names()

    if "users" not in existing:
        database.create_collection("users")

    if "sessions" not in existing:
        database.create_collection("sessions")

    if "snapshots" not in existing:
        database.create_collection("snapshots")

    database["users"].create_index("username", unique=True)
    database["sessions"].create_index("user_id")
    database["sessions"].create_index("status")
    database["snapshots"].create_index("session_id")
    database["snapshots"].create_index([("user_id", 1), ("timestamp", 1)])

    print("Database initialization complete.")


if __name__ == "__main__":
    main()