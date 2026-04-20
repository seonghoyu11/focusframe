"""Unit tests for the ML client analysis worker."""

# pylint: disable=import-error,redefined-outer-name
from unittest.mock import MagicMock, patch

import main


def test_distraction_classification_neutral_is_focused():
    """Only a neutral face counts as focused."""
    assert main.distraction_classification(("neutral", 0.9)) == "focused"
    assert main.distraction_classification(("neutral", 0.3)) == "focused"


def test_distraction_classification_other_emotions_are_distracted():
    """Every non-neutral emotion is distracted."""
    for emotion in ("happy", "sad", "angry", "fear", "disgust", "surprise"):
        assert main.distraction_classification((emotion, 0.9)) == "distracted", emotion


def test_distraction_classification_no_face_is_distracted():
    """No face detected (None data) counts as distracted."""
    assert main.distraction_classification(None) == "distracted"
    assert main.distraction_classification((None, None)) == "distracted"


def test_distraction_classification_unknown_emotion_is_distracted():
    """Unexpected emotion labels fall through to distracted."""
    assert main.distraction_classification(("unknown_label", 0.9)) == "distracted"


def test_analyze_image_bytes_empty():
    """Empty or None bytes yield (None, None)."""
    assert main.analyze_image_bytes(b"") == (None, None)
    assert main.analyze_image_bytes(None) == (None, None)


@patch("main.cv2.imdecode")
def test_analyze_image_bytes_decode_failure(mock_imdecode):
    """Corrupt image (imdecode returns None) yields (None, None)."""
    mock_imdecode.return_value = None
    assert main.analyze_image_bytes(b"garbage") == (None, None)


@patch("main.cv2.imdecode")
@patch("main.get_detector")
def test_analyze_image_bytes_success(mock_get_detector, mock_imdecode):
    """FER returning a tuple is returned as-is."""
    mock_imdecode.return_value = "fake_img"
    mock_detector = MagicMock()
    mock_detector.top_emotion.return_value = ("neutral", 0.92)
    mock_get_detector.return_value = mock_detector

    result = main.analyze_image_bytes(b"fake_jpeg_bytes")
    assert result == ("neutral", 0.92)


@patch("main.cv2.imdecode")
@patch("main.get_detector")
def test_analyze_image_bytes_no_face(mock_get_detector, mock_imdecode):
    """FER returning None (no face) yields (None, None)."""
    mock_imdecode.return_value = "fake_img"
    mock_detector = MagicMock()
    mock_detector.top_emotion.return_value = None
    mock_get_detector.return_value = mock_detector

    assert main.analyze_image_bytes(b"fake_jpeg") == (None, None)


@patch("main.set_session_notification")
@patch("main.analyze_image_bytes")
@patch("main.get_collection")
def test_process_pending_focused_does_not_notify(
    mock_get_col, mock_analyze, mock_set_notif
):
    """Focused classification updates the doc but does NOT set notification."""
    mock_analyze.return_value = ("neutral", 0.9)
    snaps = MagicMock()
    sessions = MagicMock()
    snaps.find.return_value.limit.return_value = [
        {"_id": "s1", "image": b"x", "session_id": "sess1"}
    ]
    mock_get_col.side_effect = lambda name: {
        "snapshots": snaps,
        "sessions": sessions,
    }[name]

    main.process_pending_snapshots()

    snaps.update_one.assert_called_once()
    args, _ = snaps.update_one.call_args
    assert args[0] == {"_id": "s1"}
    assert args[1]["$set"]["classification"] == "focused"
    assert args[1]["$set"]["analyzed"] is True
    mock_set_notif.assert_not_called()


@patch("main.set_session_notification")
@patch("main.analyze_image_bytes")
@patch("main.get_collection")
def test_process_pending_distracted_sets_notification(
    mock_get_col, mock_analyze, mock_set_notif
):
    """Distracted classification triggers a session notification."""
    mock_analyze.return_value = ("sad", 0.8)
    snaps = MagicMock()
    sessions = MagicMock()
    sessions.find_one.return_value = {"_id": "sess1", "status": "active"}
    snaps.find.return_value.limit.return_value = [
        {"_id": "s2", "image": b"x", "session_id": "sess1"}
    ]
    mock_get_col.side_effect = lambda name: {
        "snapshots": snaps,
        "sessions": sessions,
    }[name]

    main.process_pending_snapshots()

    mock_set_notif.assert_called_once_with("sess1", "distracted")


@patch("main.set_session_notification")
@patch("main.analyze_image_bytes")
@patch("main.get_collection")
def test_process_pending_no_face_sets_notification(
    mock_get_col, mock_analyze, mock_set_notif
):
    """No face detected -> distracted -> notification fires."""
    mock_analyze.return_value = (None, None)
    snaps = MagicMock()
    sessions = MagicMock()
    sessions.find_one.return_value = {"_id": "sess1", "status": "active"}
    snaps.find.return_value.limit.return_value = [
        {"_id": "s3", "image": b"x", "session_id": "sess1"}
    ]
    mock_get_col.side_effect = lambda name: {
        "snapshots": snaps,
        "sessions": sessions,
    }[name]

    main.process_pending_snapshots()

    mock_set_notif.assert_called_once_with("sess1", "distracted")


@patch("main.set_session_notification")
@patch("main.analyze_image_bytes")
@patch("main.get_collection")
def test_process_pending_skips_notification_if_session_inactive(
    mock_get_col, mock_analyze, mock_set_notif
):
    """Distracted on a completed session does NOT set notification."""
    mock_analyze.return_value = ("sad", 0.8)
    snaps = MagicMock()
    sessions = MagicMock()
    sessions.find_one.return_value = None  # no matching active session
    snaps.find.return_value.limit.return_value = [
        {"_id": "s4", "image": b"x", "session_id": "sess1"}
    ]
    mock_get_col.side_effect = lambda name: {
        "snapshots": snaps,
        "sessions": sessions,
    }[name]

    main.process_pending_snapshots()

    mock_set_notif.assert_not_called()
