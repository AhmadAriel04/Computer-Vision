from unittest import result

from ultralytics import YOLO
import cv2


class EmotionClassifier:

    def __init__(self, model_path):

        self.model = YOLO(str(model_path))
         
    def predict(self, face):

        face = cv2.resize(face, (224,224))

        face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)

        result = self.model.predict(
            source=face,
            verbose=False
        )[0]

        emotion = result.names[result.probs.top1].strip().lower()

        confidence = float(result.probs.top1conf)

        return emotion, confidence