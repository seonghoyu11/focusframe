"""Module for emotion detection using FER and capturing data autonomously."""

import os
import time
import datetime
from fer.fer import FER  # pylint: disable=import-error
import cv2  # pylint: disable=import-error
from pymongo import MongoClient

WAIT_TIME_SECONDS = 600
DATABASE_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "terminal_titans_db"
COLLECTION_NAME = "ml_records"

def analyze_and_store(db_collection, detector):
    """Captures an image, analyzes it for emotion, and saves to database."""
    print(f"[{datetime.datetime.now()}] Waking up to process data...")

    cap = cv2.VideoCapture(0)  # pylint: disable=no-member

    img_data = None

    if cap.isOpened():
        print("Camera detected. Taking photo...")
        time.sleep(1)
        ret, frame = cap.read()
        cap.release()

        if ret:
            img_data = frame
        else:
            print("Failed to capture from camera.")
    else:
        print("No camera found (likely inside Mac Docker test). Falling back to static image.")
        # fallback
        fallback_path = os.path.join(os.getcwd(), "img.png")
        if os.path.exists(fallback_path):
            img_data = cv2.imread(fallback_path)  # pylint: disable=no-member
        else:
            print("Fallback image 'img.png' not found either.")

    if img_data is not None:
        # Predict emotion
        detector.detect_emotions(img_data)
        result = detector.top_emotion(img_data)

        if result:
            emotion, score = result
            print(f"Detected: {emotion} (Score: {score})")

            # Save to Database
            record = {
                "timestamp": datetime.datetime.now(datetime.timezone.utc),
                "source": "automated_client",
                "emotion": emotion,
                "score": score,
                "status": "completed"
            }
            db_collection.insert_one(record)
            print("Metadata saved to MongoDB successfully.")
        else:
            print("No face detected. Skipping database insert.")
    else:
        print("No valid image data to process.")

def main():
    """Main execution entrypoint for continuous ML processing."""
    print(f"Starting connection to MongoDB at {DATABASE_URI}...")
    client = MongoClient(DATABASE_URI)
    db = client[DB_NAME]  # pylint: disable=invalid-name
    collection = db[COLLECTION_NAME]

    detector = FER(mtcnn=False)

    print(f"ML Client Initialized. Starting {WAIT_TIME_SECONDS} second interval loop.")
    while True:
        analyze_and_store(collection, detector)
        print(f"Sleeping for {WAIT_TIME_SECONDS} seconds...")
        time.sleep(WAIT_TIME_SECONDS)

if __name__ == "__main__":
    main()
