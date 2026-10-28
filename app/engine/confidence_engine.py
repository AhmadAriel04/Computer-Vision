"""
ConfidenceEngine

Menggabungkan ringkasan dari ScoreAggregator (avg_confidence, avg_quality,
dominant_emotion, sample_count) menjadi SATU skor akhir (0.0-1.0) yang
merepresentasikan seberapa yakin sistem terhadap emosi dominan yang
terdeteksi selama satu sesi. Skor ini yang dikirim ke Laravel, bukan
confidence mentah dari model per-frame.

Kenapa dipisah dari ScoreAggregator: ScoreAggregator murni agregasi data
(tidak tahu apa itu "cukup yakin"), sedangkan ConfidenceEngine yang
menentukan aturan bisnisnya (berapa sample minimal, berapa durasi
minimal, bagaimana bobot masing-masing komponen).
"""

from app.utils.config import MIN_RELIABLE_SAMPLES, MIN_RELIABLE_DURATION


class ConfidenceEngine:

    def __init__(
        self,
        min_samples: int = MIN_RELIABLE_SAMPLES,
        min_duration: float = MIN_RELIABLE_DURATION,
        weights: dict | None = None,
    ):
        self.min_samples = min_samples
        self.min_duration = min_duration

        # Bobot masing-masing komponen skor akhir, totalnya 1.0.
        self.weights = weights or {
            "avg_confidence": 0.5,   # rata-rata confidence model per-frame
            "avg_quality": 0.2,      # rata-rata kualitas frame (blur+brightness)
            "consistency": 0.3,      # seberapa dominan emosi mayoritas
        }

    def _consistency(self, summary: dict) -> float:
        """
        Rasio sample emosi dominan terhadap total sample. Semakin tinggi
        berarti emosi konsisten sepanjang sesi (bukan "loncat-loncat").
        """

        distribution = summary.get("emotion_distribution") or {}

        if not distribution:
            return 0.0

        return max(distribution.values())

    def evaluate(self, summary: dict, duration: float) -> dict:
        """
        Args:
            summary: hasil ScoreAggregator.summarize(face_id)
            duration: durasi sesi dalam detik (dari SessionManager.duration)

        Returns:
            dict berisi final_confidence (0-1), label, dan reliable (bool)
            -- reliable menandai apakah sesi ini layak dianggap valid
            sebelum dikirim ke Laravel.
        """

        sample_count = summary.get("sample_count", 0)

        reliable = (
            sample_count >= self.min_samples
            and duration >= self.min_duration
        )

        if sample_count == 0:
            return {
                "final_confidence": 0.0,
                "label": "no_data",
                "reliable": False,
            }

        consistency = self._consistency(summary)

        final_confidence = (
            self.weights["avg_confidence"] * summary.get("avg_confidence", 0.0)
            + self.weights["avg_quality"] * summary.get("avg_quality", 0.0)
            + self.weights["consistency"] * consistency
        )

        final_confidence = round(min(max(final_confidence, 0.0), 1.0), 4)

        if not reliable:
            label = "insufficient_data"
        elif final_confidence >= 0.75:
            label = "high"
        elif final_confidence >= 0.5:
            label = "medium"
        else:
            label = "low"

        return {
            "final_confidence": final_confidence,
            "label": label,
            "reliable": reliable,
        }
