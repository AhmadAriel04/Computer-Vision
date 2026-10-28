"""
ScoreAggregator

Mengumpulkan sample (emotion, confidence, quality_score) per face_id selama
sesi berjalan, lalu meringkasnya menjadi satu snapshot saat sesi selesai.
Ringkasan ini yang nanti dipakai ConfidenceEngine untuk menghitung skor akhir,
lalu dikirim APIClient ke Laravel.
"""

from collections import Counter, defaultdict


class ScoreAggregator:

    def __init__(self):
        # face_id -> list of {"emotion": str, "confidence": float, "quality_score": float}
        self.samples = defaultdict(list)

    def add_sample(
        self,
        face_id,
        emotion: str,
        confidence: float,
        quality_score: float
    ):
        emotion = (
            str(emotion)
            .strip()
            .lower()
        )

        self.samples[face_id].append({
            "emotion": emotion,
            "confidence": float(confidence),
            "quality_score": float(quality_score),
        })

    def summarize(self, face_id) -> dict:
        """
        Ringkasan sample untuk satu wajah. Aman dipanggil walau belum ada
        sample sama sekali (misal sesi berakhir sebelum sempat ada frame
        berkualitas baik) -- akan balikin nilai default 0/"Unknown".
        """

        rows = self.samples.get(face_id, [])

        if not rows:
            return {
                "sample_count": 0,
                "dominant_emotion": "Unknown",
                "emotion_distribution": {},
                "avg_confidence": 0.0,
                "avg_quality": 0.0,
            }

        # "Unknown" (confidence di bawah EMOTION_CONF) tidak dihitung ke
        # distribusi/dominant emotion kecuali memang semua sample-nya Unknown.
        known = [r for r in rows if r["emotion"] != "Unknown"]
        counted = known if known else rows

        distribution = Counter(r["emotion"] for r in counted)
        total = sum(distribution.values())

        emotion_distribution = {
            emotion: round(count / total, 3)
            for emotion, count in distribution.items()
        }

        dominant_emotion = distribution.most_common(1)[0][0]

        avg_confidence = sum(r["confidence"] for r in rows) / len(rows)
        avg_quality = sum(r["quality_score"] for r in rows) / len(rows)

        return {
            "sample_count": len(rows),
            "dominant_emotion": dominant_emotion,
            "emotion_distribution": emotion_distribution,
            "avg_confidence": round(avg_confidence, 3),
            "avg_quality": round(avg_quality, 3),
        }

    def clear(self, face_id):
        self.samples.pop(face_id, None)
