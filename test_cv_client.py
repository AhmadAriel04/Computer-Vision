from app.services.cv_client import CVClient


client = CVClient()

payload = {
    "session_uid": "TEST-PYTHON-CV-001",
    "counter_code": "CS-01",

    "started_at": "2026-09-09T10:00:00+00:00",
    "ended_at": "2026-09-09T10:00:10+00:00",

    "duration_seconds": 10,

    "rating": 4,
    "score": 4.20,
    "confidence": 0.78,

    "dominant_emotion": "happy",

    "distribution": {
        "happy": 0.70,
        "neutral": 0.20,
        "sad": 0.07,
        "angry": 0.03,
    },

    "valence": 0.614,

    "frames_seen": 300,
    "samples_used": 60,
    "effective_samples": 45.5,

    "confidence_components": {
        "adequacy": 1.0,
        "agreement": 0.70,
        "stability": 0.70,
        "model": 0.80,
        "quality": 0.78,
        "decisiveness": 0.70,
    },

    "model_version": "emotion-v1",
}


response = client.send_session(
    payload
)

print()
print("=== HASIL ===")
print(response)