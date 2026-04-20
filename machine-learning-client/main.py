"""ML client for FocusFrame — analysis worker.

Classification is simple:
    neutral face -> "focused"
    anything else -> "distracted"
"""

import datetime
import os
import time

import cv2  # pylint: disable=import-error
import numpy as np  # pylint: disable=import-error
from dotenv import load_dotenv
from fer.fer import FER  # pylint: disable=import-error

from db import (
    SESSIONS_COLLECTION,
    SNAPSHOTS_COLLECTION,
    get_collection,
    set_session_notification,
)

load_dotenv()

_DETECTOR = None


def get_detector():
    """Return a shared FER instance, loaded on first use."""
    global _DETECTOR  # pylint: disable=global-statement
    if _DETECTOR is None:
        _DETECTOR = FER(mtcnn=False)
    return _DETECTOR


def analyze_image_bytes(image_bytes):
    """Decode JPEG bytes, run FER, return (emotion, score).

    Returns (None, None) if decoding fails or no face is detected.
    """
    if not image_bytes:
        return None, None
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)  # pylint: disable=no-member
    if img is None:
        return None, None
    result = get_detector().top_emotion(img)
    if result is None:
        return None, None
    return result


def distraction_classification(data):
    """Classify a (emotion, score) tuple — or None — as focused or distracted.

    Only a neutral face counts as focused. Everything else — including
    no face detected, happy, angry, sad, etc. — is distracted.
    """
    if data is None or data[0] is None:
        return "distracted"
    emotion, _ = data
    if emotion == "neutral":
        return "focused"
    return "distracted"


def process_pending_snapshots(batch_size=20):
    """Find unanalyzed snapshots, classify them, write results back."""
    snapshots = get_collection(SNAPSHOTS_COLLECTION)
    sessions = get_collection(SESSIONS_COLLECTION)
    pending = snapshots.find({"analyzed": False}).limit(batch_size)

    for snap in pending:
        emotion_data = analyze_image_bytes(snap.get("image", b""))
        classification = distraction_classification(emotion_data)
        emotion = emotion_data[0] if emotion_data and emotion_data[0] else None
        confidence = emotion_data[1] if emotion_data and emotion_data[1] else 0.0

        snapshots.update_one(
            {"_id": snap["_id"]},
            {
                "$set": {
                    "emotion": emotion,
                    "confidence": confidence,
                    "classification": classification,
                    "analyzed": True,
                    "analyzed_at": datetime.datetime.now(datetime.timezone.utc),
                }
            },
        )
        print(
            f"Analyzed snapshot {snap['_id']}: {classification} "
            f"(emotion={emotion}, conf={confidence})"
        )

        # Only flag the session if it's still active.
        if classification == "distracted":
            is_active = sessions.find_one(
                {"_id": snap["session_id"], "status": "active"}
            )
            if is_active:
                set_session_notification(snap["session_id"], classification)


def run_loop():
    """Poll for unanalyzed snapshots forever."""
    print("FocusFrame ML Client (analysis worker) starting...")
    interval = int(os.getenv("ANALYSIS_INTERVAL_SECONDS", "3"))
    while True:
        try:
            process_pending_snapshots()
        except Exception as err:  # pylint: disable=broad-exception-caught
            print(f"Error during analysis pass: {err}")
        time.sleep(interval)


if __name__ == "__main__":
    run_loop()
