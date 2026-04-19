"""ML client for FocusFrame study monitoring."""

import os
import time
import uuid
import base64
import datetime
import cv2  # pylint: disable=import-error

from db import get_active_session, save_snapshot, update_session_notification

FER = None

CAPTURE_INTERVAL_SECONDS = int(os.environ.get("CAPTURE_INTERVAL_SECONDS", "30"))
IMAGE_DIR = "captured_images"


def ensure_image_dir():
    """Create image directory if it does not exist."""
    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)


def capture_image():
    """Capture one frame from webcam or fall back to img.png."""
    cap = cv2.VideoCapture(0)  # pylint: disable=no-member
    img_data = None

    if cap.isOpened():
        ret, frame = cap.read()
        cap.release()
        if ret:
            img_data = frame
        else:
            print("Failed to capture from camera.")
    else:
        print("No camera found. Falling back to static image.")
        fallback_path = os.path.join(os.getcwd(), "img.png")
        if os.path.exists(fallback_path):
            img_data = cv2.imread(fallback_path)  # pylint: disable=no-member
        else:
            print("Fallback image 'img.png' not found.")

    return img_data


def save_image_locally(frame):
    """Save image locally and return file path."""
    ensure_image_dir()
    filename = f"{uuid.uuid4()}.jpg"
    filepath = os.path.join(IMAGE_DIR, filename)
    cv2.imwrite(filepath, frame)  # pylint: disable=no-member
    return filepath


def encode_image_base64(frame):
    """Encode image frame as base64 string for MongoDB storage."""
    success, buffer = cv2.imencode(".jpg", frame)  # pylint: disable=no-member
    if not success:
        return None
    return base64.b64encode(buffer).decode("utf-8")


def classify_state(face_detected, dominant_emotion):
    """Classify user state as focused, distracted, or absent."""
    if not face_detected:
        return "absent"

    if dominant_emotion in {"neutral", "happy"}:
        return "focused"

    if dominant_emotion in {"sad", "angry", "fear", "disgust", "surprise"}:
        return "distracted"

    return "distracted"


def analyze_frame(detector, frame):
    """Run FER and return face detection, dominant emotion, confidence, and raw output."""
    detections = detector.detect_emotions(frame)

    if not detections:
        return {
            "face_detected": False,
            "dominant_emotion": None,
            "confidence": 0.0,
            "all_emotions": {},
        }

    emotions = detections[0]["emotions"]
    dominant_emotion = max(emotions, key=emotions.get)
    confidence = emotions[dominant_emotion]

    return {
        "face_detected": True,
        "dominant_emotion": dominant_emotion,
        "confidence": confidence,
        "all_emotions": emotions,
    }


def process_active_session(detector, session):
    """Capture, analyze, classify, and store one snapshot for an active session."""
    frame = capture_image()
    if frame is None:
        print("No valid image data to process.")
        return

    timestamp = datetime.datetime.now(datetime.timezone.utc)
    image_path = save_image_locally(frame)
    image_data = encode_image_base64(frame)

    analysis = analyze_frame(detector, frame)
    classification = classify_state(
        analysis["face_detected"], analysis["dominant_emotion"]
    )

    snapshot = {
        "session_id": session["_id"],
        "user_id": session["user_id"],
        "timestamp": timestamp,
        "image_path": image_path,
        "image_data": image_data,
        "emotion": {
            "dominant": analysis["dominant_emotion"],
            "confidence": analysis["confidence"],
            "all_emotions": analysis["all_emotions"],
        },
        "face_detected": analysis["face_detected"],
        "classification": classification,
    }

    save_snapshot(snapshot)
    print(f"Saved snapshot with classification: {classification}")

    if classification == "distracted":
        update_session_notification(
            session["_id"],
            "distracted",
            "You seem distracted! Get back to studying.",
        )
    elif classification == "absent":
        update_session_notification(
            session["_id"],
            "absent",
            "We can't see your face. Are you away from your study session?",
        )


def main():
    """Main polling loop for FocusFrame."""
    fer_class = FER

    if fer_class is None:
        from fer.fer import FER as runtime_fer  # pylint: disable=import-error
        fer_class = runtime_fer

    detector = fer_class(mtcnn=False)

    while True:
        active_session = get_active_session()

        if active_session:
            print("Active session found. Processing snapshot...")
            process_active_session(detector, active_session)
        else:
            print("No active session found.")

        time.sleep(CAPTURE_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
