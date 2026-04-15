"""Module for emotion detection using FER and capturing data autonomously."""

import os
import time
import datetime
from fer.fer import FER  # pylint: disable=import-error
import cv2  # pylint: disable=import-error
from db import save_record

def analyze_and_store():
    """Captures an image, analyzes it for emotion, and saves it utilizing db.py."""
    print(f"[{datetime.datetime.now()}] Waking up to process data...")
    detector = FER(mtcnn=False)

    cap = cv2.VideoCapture(0)  # pylint: disable=no-member

    img_data = None

    if cap.isOpened():
        print("Camera detected. Taking photo...")
        time.sleep(3)
        ret, frame = cap.read()
        cap.release()

        if ret:
            img_data = frame
        else:
            print("Failed to capture from camera.")
    else:
        print("No camera found (likely inside Mac Docker test). Falling back to static image.")
        fallback_path = os.path.join(os.getcwd(), "img.png")
        if os.path.exists(fallback_path):
            img_data = cv2.imread(fallback_path)  # pylint: disable=no-member
        else:
            print("Fallback image 'img.png' not found either.")

    if img_data is not None:
        detector.detect_emotions(img_data)
        result = detector.top_emotion(img_data)

        if result:
            emotion, score = result
            print(f"Detected: {emotion} (Score: {score})")

            record = {
                "timestamp": datetime.datetime.now(datetime.timezone.utc),
                "source": "webcam",
                "emotion": emotion,
                "score": score,
                "status": "completed"
            }
            save_record(record)
            print("Metadata saved to MongoDB successfully.")
        else:
            print("No face detected. Skipping database insert.")
    else:
        print("No valid image data to process.")

if __name__ == "__main__":
    analyze_and_store()
