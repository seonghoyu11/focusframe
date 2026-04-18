"""Module for emotion detection using FER and capturing data autonomously."""

import os
import time
import datetime
from fer.fer import FER  # pylint: disable=import-error
import cv2  # pylint: disable=import-error
from db import save_record


def get_face_emotion():
    """Gets face emotion."""
    detector = FER(mtcnn=False)

    cap = cv2.VideoCapture(0)  # pylint: disable=no-member

    img_data = None

    if cap.isOpened():
        time.sleep(3)
        ret, frame = cap.read()
        cap.release()

        if ret:
            img_data = frame
    else:
        # when there is an error, use a fallback image
        fallback_path = os.path.join(os.getcwd(), "img.png")
        if os.path.exists(fallback_path):
            img_data = cv2.imread(fallback_path)  # pylint: disable=no-member

    if img_data is not None:
        detector.detect_emotions(img_data)
        result = detector.top_emotion(img_data)
        return result
    else:
        return None

def distraction_classification(data):
    """Classifies distraction based on emotion data."""
    if data is None:
        return "absent"
    emotion, score = data
    if emotion in ["happy", "neutral", "angry"]:
        return "focused"
    elif emotion in ["sad", "fear", "disgust", "surprise"]:
        return "distracted"
    else:
        return "unknown"

def store_data(emotion, score, classification):
    """Stores data in MongoDB."""
    