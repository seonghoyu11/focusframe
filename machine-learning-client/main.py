# skeleton file

from fer.fer import FER
import cv2
import os
import pprint

img_lst = ["img_png"] # put your image file names here, e.g. ["img1.jpg", "img2.png"]
count = 1
for img in img_lst:
    img_path = os.path.join(os.getcwd(), img)
    if not os.path.exists(img_path):
        print(f"Error: File '{img_path}' not found in {os.getcwd()}")
    else:
        img_data = cv2.imread(img_path)
        detector = FER(mtcnn=False)
        detector.detect_emotions(img_data)

        result = detector.top_emotion(img_data)
        if result:
                emotion, score = result
                pprint.pprint(result)
                print(f"Result {count}: {emotion} with a score of {score}")
        else:
            print("No face detected. Try an image with a clearer face.")
    count += 1
