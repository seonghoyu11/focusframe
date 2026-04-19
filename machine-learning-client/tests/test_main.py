"""Unit tests for ML client main logic."""

# pylint: disable=missing-function-docstring,missing-class-docstring
# pylint: disable=too-few-public-methods,unused-argument

import datetime
import pytest
import main  # pylint: disable=import-error


class FakeDetectorNoFace:
    def detect_emotions(self, frame):
        return []


class FakeDetectorFace:
    def detect_emotions(self, frame):
        return [
            {
                "emotions": {
                    "angry": 0.01,
                    "disgust": 0.01,
                    "fear": 0.02,
                    "happy": 0.05,
                    "sad": 0.03,
                    "surprise": 0.04,
                    "neutral": 0.84,
                }
            }
        ]


def test_classify_state_absent():
    assert main.classify_state(False, None) == "absent"


def test_classify_state_focused():
    assert main.classify_state(True, "neutral") == "focused"
    assert main.classify_state(True, "happy") == "focused"


def test_classify_state_distracted():
    assert main.classify_state(True, "sad") == "distracted"
    assert main.classify_state(True, "angry") == "distracted"
    assert main.classify_state(True, "fear") == "distracted"
    assert main.classify_state(True, "disgust") == "distracted"
    assert main.classify_state(True, "surprise") == "distracted"


def test_analyze_frame_no_face():
    detector = FakeDetectorNoFace()
    result = main.analyze_frame(detector, frame="fake-frame")

    assert result["face_detected"] is False
    assert result["dominant_emotion"] is None
    assert result["confidence"] == 0.0
    assert result["all_emotions"] == {}


def test_analyze_frame_with_face():
    detector = FakeDetectorFace()
    result = main.analyze_frame(detector, frame="fake-frame")

    assert result["face_detected"] is True
    assert result["dominant_emotion"] == "neutral"
    assert result["confidence"] == 0.84
    assert "happy" in result["all_emotions"]


def test_process_active_session_saves_focused_snapshot(monkeypatch):
    saved = {}

    session = {"_id": "session123", "user_id": "user456"}

    monkeypatch.setattr(main, "capture_image", lambda: "fake-frame")
    monkeypatch.setattr(main, "save_image_locally", lambda frame: "captured/test.jpg")
    monkeypatch.setattr(main, "encode_image_base64", lambda frame: "encoded-image")
    monkeypatch.setattr(
        main,
        "analyze_frame",
        lambda detector, frame: {
            "face_detected": True,
            "dominant_emotion": "neutral",
            "confidence": 0.91,
            "all_emotions": {"neutral": 0.91},
        },
    )

    def fake_save_snapshot(snapshot):
        saved["snapshot"] = snapshot

    notifications = []

    def fake_update_session_notification(session_id, notification_type, message):
        notifications.append((session_id, notification_type, message))

    monkeypatch.setattr(main, "save_snapshot", fake_save_snapshot)
    monkeypatch.setattr(main, "update_session_notification", fake_update_session_notification)

    main.process_active_session(detector="fake-detector", session=session)

    snapshot = saved["snapshot"]
    assert snapshot["session_id"] == "session123"
    assert snapshot["user_id"] == "user456"
    assert snapshot["image_path"] == "captured/test.jpg"
    assert snapshot["image_data"] == "encoded-image"
    assert snapshot["emotion"]["dominant"] == "neutral"
    assert snapshot["classification"] == "focused"
    assert snapshot["face_detected"] is True
    assert isinstance(snapshot["timestamp"], datetime.datetime)
    assert not notifications


def test_process_active_session_sets_distracted_notification(monkeypatch):
    session = {"_id": "session123", "user_id": "user456"}
    notifications = []

    monkeypatch.setattr(main, "capture_image", lambda: "fake-frame")
    monkeypatch.setattr(main, "save_image_locally", lambda frame: "captured/test.jpg")
    monkeypatch.setattr(main, "encode_image_base64", lambda frame: "encoded-image")
    monkeypatch.setattr(
        main,
        "analyze_frame",
        lambda detector, frame: {
            "face_detected": True,
            "dominant_emotion": "sad",
            "confidence": 0.77,
            "all_emotions": {"sad": 0.77},
        },
    )
    monkeypatch.setattr(main, "save_snapshot", lambda snapshot: None)

    def fake_update_session_notification(session_id, notification_type, message):
        notifications.append((session_id, notification_type, message))

    monkeypatch.setattr(main, "update_session_notification", fake_update_session_notification)

    main.process_active_session(detector="fake-detector", session=session)

    assert notifications == [
        ("session123", "distracted", "You seem distracted! Get back to studying.")
    ]


def test_process_active_session_sets_absent_notification(monkeypatch):
    session = {"_id": "session123", "user_id": "user456"}
    notifications = []

    monkeypatch.setattr(main, "capture_image", lambda: "fake-frame")
    monkeypatch.setattr(main, "save_image_locally", lambda frame: "captured/test.jpg")
    monkeypatch.setattr(main, "encode_image_base64", lambda frame: "encoded-image")
    monkeypatch.setattr(
        main,
        "analyze_frame",
        lambda detector, frame: {
            "face_detected": False,
            "dominant_emotion": None,
            "confidence": 0.0,
            "all_emotions": {},
        },
    )
    monkeypatch.setattr(main, "save_snapshot", lambda snapshot: None)

    def fake_update_session_notification(session_id, notification_type, message):
        notifications.append((session_id, notification_type, message))

    monkeypatch.setattr(main, "update_session_notification", fake_update_session_notification)

    main.process_active_session(detector="fake-detector", session=session)

    assert notifications == [
        (
            "session123",
            "absent",
            "We can't see your face. Are you away from your study session?",
        )
    ]


def test_process_active_session_returns_when_no_frame(monkeypatch):
    called = {"save_snapshot": False}

    monkeypatch.setattr(main, "capture_image", lambda: None)

    def fake_save_snapshot(snapshot):
        called["save_snapshot"] = True

    monkeypatch.setattr(main, "save_snapshot", fake_save_snapshot)

    main.process_active_session(detector="fake-detector", session={"_id": "s1", "user_id": "u1"})

    assert called["save_snapshot"] is False


def test_main_calls_process_when_active_session_exists(monkeypatch):
    calls = {"processed": 0, "slept": 0}

    class FakeFer:
        def __init__(self, mtcnn=False):
            self.mtcnn = mtcnn

    monkeypatch.setattr(main, "FER", FakeFer)
    monkeypatch.setattr(main, "get_active_session", lambda: {"_id": "s1", "user_id": "u1"})

    def fake_process(detector, session):
        calls["processed"] += 1

    def fake_sleep(seconds):
        calls["slept"] += 1
        raise KeyboardInterrupt

    monkeypatch.setattr(main, "process_active_session", fake_process)
    monkeypatch.setattr(main.time, "sleep", fake_sleep)

    with pytest.raises(KeyboardInterrupt):
        main.main()

    assert calls["processed"] == 1
    assert calls["slept"] == 1


def test_main_skips_process_when_no_active_session(monkeypatch):
    calls = {"processed": 0, "slept": 0}

    class FakeFer:
        def __init__(self, mtcnn=False):
            self.mtcnn = mtcnn

    monkeypatch.setattr(main, "FER", FakeFer)
    monkeypatch.setattr(main, "get_active_session", lambda: None)

    def fake_process(detector, session):
        calls["processed"] += 1

    def fake_sleep(seconds):
        calls["slept"] += 1
        raise KeyboardInterrupt

    monkeypatch.setattr(main, "process_active_session", fake_process)
    monkeypatch.setattr(main.time, "sleep", fake_sleep)

    with pytest.raises(KeyboardInterrupt):
        main.main()

    assert calls["processed"] == 0
    assert calls["slept"] == 1
