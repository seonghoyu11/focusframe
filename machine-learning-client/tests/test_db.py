import datetime
import db


class FakeSessionsCollection:
    def __init__(self):
        self.find_one_query = None
        self.update_one_filter = None
        self.update_one_update = None

    def find_one(self, query):
        self.find_one_query = query
        return {"_id": "session123", "status": "active"}

    def update_one(self, filter_query, update_query):
        self.update_one_filter = filter_query
        self.update_one_update = update_query


class FakeSnapshotsCollection:
    def __init__(self):
        self.inserted = None

    def insert_one(self, snapshot):
        self.inserted = snapshot


class FakeDatabase:
    def __init__(self):
        self.sessions = FakeSessionsCollection()
        self.snapshots = FakeSnapshotsCollection()

    def __getitem__(self, key):
        if key == "sessions":
            return self.sessions
        if key == "snapshots":
            return self.snapshots
        raise KeyError(key)


def test_get_active_session(monkeypatch):
    fake_db = FakeDatabase()
    monkeypatch.setattr(db, "get_database", lambda: fake_db)

    result = db.get_active_session()

    assert result == {"_id": "session123", "status": "active"}
    assert fake_db.sessions.find_one_query == {"status": "active"}


def test_save_snapshot(monkeypatch):
    fake_db = FakeDatabase()
    monkeypatch.setattr(db, "get_database", lambda: fake_db)

    snapshot = {"session_id": "s1", "classification": "focused"}
    db.save_snapshot(snapshot)

    assert fake_db.snapshots.inserted == snapshot


def test_update_session_notification(monkeypatch):
    fake_db = FakeDatabase()
    monkeypatch.setattr(db, "get_database", lambda: fake_db)

    db.update_session_notification("session123", "distracted", "Focus please")

    assert fake_db.sessions.update_one_filter == {"_id": "session123"}

    notification = fake_db.sessions.update_one_update["$set"]["notification"]
    assert notification["type"] == "distracted"
    assert notification["message"] == "Focus please"
    assert isinstance(notification["timestamp"], datetime.datetime)
    