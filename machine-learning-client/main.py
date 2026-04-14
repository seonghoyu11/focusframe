"""Module for emotion detection using FER."""

import os
import pprint

from fer.fer import FER  # pylint: disable=import-error
import cv2  # pylint: disable=import-error

img_lst = ["img.png"]  # put your image file names here, e.g. ["img1.jpg", "img2.png"]
image_count = 1  # pylint: disable=invalid-name
for img in img_lst:
    img_path = os.path.join(os.getcwd(), img)
    if not os.path.exists(img_path):
        print(f"Error: File '{img_path}' not found in {os.getcwd()}")
    else:
        img_data = cv2.imread(img_path)  # pylint: disable=no-member
        detector = FER(mtcnn=False)
        detector.detect_emotions(img_data)

        result = detector.top_emotion(img_data)
        if result:
            emotion, score = result
            pprint.pprint(result)
            print(f"Result {image_count}: {emotion} with a score of {score}")
        else:
            print("No face detected. Try an image with a clearer face.")
    image_count += 1
