"""ML client for FocusFrame study monitoring."""

import datetime
import os
import time

import cv2  # pylint: disable=import-error
from dotenv import load_dotenv
from fer.fer import FER  # pylint: disable=import-error

from db import (
    SESSIONS_COLLECTION,
    get_collection,
    save_snapshot,
    set_session_notification,
)

load_dotenv()


def get_face_emotion():
    """Capture a frame and return image data with top emotion."""
    detector = FER(mtcnn=False)
    cap = cv2.VideoCapture(0)  # pylint: disable=no-member
    img_data = None

    if cap.isOpened():
        time.sleep(3)
        ret, cap_frame = cap.read()
        cap.release()
        if ret:
            img_data = cap_frame
    else:
        # when there is an error, use a fallback image
        fallback_path = os.path.join(os.getcwd(), "img.png")
        if os.path.exists(fallback_path):
            img_data = cv2.imread(fallback_path)  # pylint: disable=no-member

    if img_data is not None:
        detector.detect_emotions(img_data)
        result = detector.top_emotion(img_data)
        return img_data, result
    return None, None


def distraction_classification(data):
    """Classifies distraction based on emotion data."""
    if data is None:
        return "absent"
    emotion, _ = data
    if emotion in ["happy", "neutral", "angry"]:
        return "focused"
    if emotion in ["sad", "fear", "disgust", "surprise"]:
        return "distracted"
    return "unknown"


def store_data(img_frame, emotion, score, classification):
    """Fetches the active session and stores the snapshot data in MongoDB.

    Returns:
        The ObjectId of the active session if storage succeeded, else None.
    """
    sessions_col = get_collection(SESSIONS_COLLECTION)
    active_session = sessions_col.find_one({"status": "active"})

    if not active_session:
        print("No active focus session found. Skipping storage.")
        return None

    success, buffer = cv2.imencode(".jpg", img_frame)  # pylint: disable=no-member
    if not success:
        print("Failed to encode image. Skipping storage.")
        return None
    image_bytes = buffer.tobytes()

    snapshot = {
        "user_id": active_session.get("user_id"),
        "session_id": active_session.get("_id"),
        "timestamp": datetime.datetime.now(datetime.timezone.utc),
        "emotion": emotion,
        "confidence": score,
        "classification": classification,
        "image": image_bytes,
    }

    save_snapshot(snapshot)
    sessions_col.update_one(
        {"_id": active_session["_id"]},
        {"$inc": {"snapshot_count": 1}},
    )
    print(f"Snapshot stored successfully for session {active_session['_id']}")
    return active_session["_id"]


def run_loop():
    """Main capture + analyze + store loop."""
    print("FocusFrame ML Client starting...")
    while True:
        frame, emotion_data = get_face_emotion()

        if frame is not None:
            if emotion_data is not None:
                emo, conf = emotion_data
                classification = distraction_classification(emotion_data)
            else:
                # Camera worked but FER found no face -> student is absent.
                emo, conf = None, 0.0
                classification = "absent"

            print(f"Classification: {classification} (emotion={emo}, conf={conf})")
            session_id = store_data(frame, emo, conf, classification)

            if session_id is not None and classification in ("distracted", "absent"):
                set_session_notification(session_id, classification)
        else:
            print("No image captured (camera unavailable).")

        interval = int(os.getenv("CAPTURE_INTERVAL_SECONDS", "10"))
        time.sleep(interval)


if __name__ == "__main__":
    run_loop()
