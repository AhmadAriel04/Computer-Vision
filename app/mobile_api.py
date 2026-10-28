
import asyncio

import cv2
import numpy as np

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

from app.detector.face_detector import FaceDetector
from app.detector.emotion_classifier import EmotionClassifier
from app.quality.frame_quality import FrameQualityCalculator
from app.utils.config import (
    FACE_MODEL,
    EMOTION_MODEL,
    EMOTION_CONF,
    MODEL_VERSION,
)

app = FastAPI(title="BSI Mobile Computer Vision API")

# Model dimuat satu kali saat server dimulai.
face_detector = FaceDetector(FACE_MODEL)
emotion_classifier = EmotionClassifier(EMOTION_MODEL)
quality_calculator = FrameQualityCalculator()

# Mencegah inferensi dari beberapa koneksi berjalan bersamaan
# pada instance model yang sama.
inference_lock = asyncio.Lock()


def analyze_frame(frame):
    height, width = frame.shape[:2]
    faces = face_detector.detect(frame)
    results = []

    for detected in faces:
        x1, y1, x2, y2 = detected["box"]

        # Pastikan koordinat crop berada dalam batas gambar.
        x1 = max(0, min(int(x1), width - 1))
        y1 = max(0, min(int(y1), height - 1))
        x2 = max(0, min(int(x2), width))
        y2 = max(0, min(int(y2), height))

        if x2 <= x1 or y2 <= y1:
            continue

        crop = frame[y1:y2, x1:x2]

        if crop.size == 0:
            continue

        quality = quality_calculator.compute(crop)

        # Prediksi ekspresi menggunakan classifier milik proyek.
        emotion, confidence = emotion_classifier.predict(crop)

        # Confidence rendah tidak ditampilkan sebagai kelas pasti.
        if confidence < EMOTION_CONF:
            emotion = "unknown"

        results.append({
            "box": [x1, y1, x2, y2],
            "face_confidence": round(
                float(detected["confidence"]), 4
            ),
            "expression": emotion,
            "confidence": round(float(confidence), 4),
            "quality_score": quality["quality_score"],
            "quality_ok": quality["is_good"],
        })

    return {
        "frame_width": width,
        "frame_height": height,
        "model_version": MODEL_VERSION,
        "faces": results,
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.websocket("/ws/detect")
async def detect_socket(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            # Flutter mengirim satu frame JPEG sebagai bytes.
            image_bytes = await websocket.receive_bytes()

            buffer = np.frombuffer(
                image_bytes, dtype=np.uint8
            )
            frame = cv2.imdecode(
                buffer, cv2.IMREAD_COLOR
            )

            if frame is None:
                await websocket.send_json({
                    "error": "Frame JPEG tidak valid"
                })
                continue

            # Inferensi dijalankan di thread worker agar event loop
            # tidak terblokir oleh proses model.
            async with inference_lock:
                result = await run_in_threadpool(
                    analyze_frame, frame
                )

            await websocket.send_json(result)

    except WebSocketDisconnect:
        print("[Mobile API] Client terputus.")
