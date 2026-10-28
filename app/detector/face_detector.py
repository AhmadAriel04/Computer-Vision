from ultralytics import YOLO

from app.utils.config import FACE_CONF


class FaceDetector:

    def __init__(self, model_path, conf=FACE_CONF):

        self.model = YOLO(str(model_path))
        self.conf = conf

    def detect(self, frame):

        results = self.model.predict(
            source=frame,
            conf=self.conf,
            verbose=False
        )

        faces = []

        if not results:
            return faces

        for box in results[0].boxes:

            x1, y1, x2, y2 = map(int, box.xyxy[0])

            faces.append({
                "box": (x1, y1, x2, y2),
                "confidence": float(box.conf[0])
            })

        return faces