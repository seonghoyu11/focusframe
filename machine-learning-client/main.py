"""ML client for detecting whether a student is present and likely studying."""

import os
import time
import uuid
import datetime
from fer.fer import FER  # pylint: disable=import-error
import cv2  # pylint: disable=import-error
from db import save_record

CAPTURE_DELAY_SECONDS = 3
IMAGE_DIR = "captured_images"


def ensure_image_dir():
    """Create the image directory if it does not already exist."""
    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)


def save_image(frame):
    """Save the captured image locally and return the file path."""
    ensure_image_dir()
    filename = f"{uuid.uuid4()}.png"
    filepath = os.path.join(IMAGE_DIR, filename)
    cv2.imwrite(filepath, frame)  # pylint: disable=no-member
    return filepath


def capture_image():
    """Capture an image from webcam or fall back to a local test image."""
    cap = cv2.VideoCapture(0)  # pylint: disable=no-member
    img_data = None

    if cap.isOpened():
        print("Camera detected. Taking photo...")
        time.sleep(CAPTURE_DELAY_SECONDS)
        ret, frame = cap.read()
        cap.release()

        if ret:
            img_data = frame
        else:
            print("Failed to capture from camera.")
    else:
        print(
            "No camera found (likely inside Docker test). "
            "Falling back to static image."
        )
        fallback_path = os.path.join(os.getcwd(), "img.png")
        if os.path.exists(fallback_path):
            img_data = cv2.imread(fallback_path)  # pylint: disable=no-member
        else:
            print("Fallback image 'img.png' not found either.")

    return img_data


def analyze_and_store():
    """Detect whether a student is present and save result to MongoDB."""
    print(f"[{datetime.datetime.now()}] Waking up to process data...")

    detector = FER(mtcnn=False)
    img_data = capture_image()

    if img_data is None:
        print("No valid image data to process.")
        return

    image_path = save_image(img_data)

    detections = detector.detect_emotions(img_data)

    if detections:
        analysis = "studying"
        warning = None
        face_detected = True
        face_count = len(detections)
        print("Face detected. Marking status as studying.")
    else:
        analysis = "distracted"
        warning = "Face not visible"
        face_detected = False
        face_count = 0
        print("No face detected. Marking status as distracted.")

    record = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc),
        "source": "webcam",
        "analysis": analysis,
        "warning": warning,
        "face_detected": face_detected,
        "face_count": face_count,
        "image_path": image_path,
        "status": "completed",
    }

    save_record(record)
    print("Metadata saved to MongoDB successfully.")


if __name__ == "__main__":
    analyze_and_store()
