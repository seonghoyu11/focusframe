"""Unit tests for ML client database helpers."""

# pylint: disable=import-error,redefined-outer-name,unused-argument
import mongomock
import pytest

import db


@pytest.fixture(autouse=True)
def mock_mongo_client(monkeypatch):
    """Mock the MongoClient in db using mongomock for every test."""
    client = mongomock.MongoClient()
    monkeypatch.setattr(db, "MongoClient", lambda *args, **kwargs: client)
    return client


def test_get_collection():
    """get_collection returns a collection bound to the configured DB."""
    collection = db.get_collection("test_col")
    assert collection.name == "test_col"
    assert collection.database.name == db.DB_NAME


def test_save_snapshot():
    """save_snapshot inserts into the snapshots collection."""
    snapshot = {"emotion": "neutral", "confidence": 0.9, "classification": "focused"}
    db.save_snapshot(snapshot)

    collection = db.get_collection(db.SNAPSHOTS_COLLECTION)
    inserted = collection.find_one({"emotion": "neutral"})
    assert inserted is not None
    assert inserted["classification"] == "focused"


def test_save_record_is_alias_for_save_snapshot():
    """save_record writes into the snapshots collection just like save_snapshot."""
    record = {"emotion": "sad", "confidence": 0.8, "classification": "distracted"}
    db.save_record(record)

    collection = db.get_collection(db.SNAPSHOTS_COLLECTION)
    inserted = collection.find_one({"emotion": "sad"})
    assert inserted is not None
    assert inserted["classification"] == "distracted"


def test_set_session_notification_distracted():
    """sends a notification if user is distracted"""
    sessions = db.get_collection(db.SESSIONS_COLLECTION)
    result = sessions.insert_one({"status": "active"})
    sess_id = result.inserted_id

    db.set_session_notification(sess_id, "distracted")

    updated = sessions.find_one({"_id": sess_id})
    assert updated.get("notification") is not None
    assert updated["notification"]["type"] == "distracted"
    assert "Refocus" in updated["notification"]["message"]
    assert updated["notification"]["timestamp"] is not None


def test_set_session_notification_focused_is_noop():
    """does not send a notification if user is focused"""
    sessions = db.get_collection(db.SESSIONS_COLLECTION)
    result = sessions.insert_one({"status": "active"})
    sess_id = result.inserted_id

    db.set_session_notification(sess_id, "focused")

    updated = sessions.find_one({"_id": sess_id})
    assert updated.get("notification") is None


def test_set_session_notification_unknown_is_noop():
    """An unknown classification label is silently ignored."""
    sessions = db.get_collection(db.SESSIONS_COLLECTION)
    result = sessions.insert_one({"status": "active"})
    sess_id = result.inserted_id

    db.set_session_notification(sess_id, "something_else")

    updated = sessions.find_one({"_id": sess_id})
    assert updated.get("notification") is None
