"""
FrameQualityCalculator

Menilai kualitas crop wajah SEBELUM sample-nya dipakai untuk skor akhir sesi,
berdasarkan dua metrik:

- Blur       : variance of Laplacian. Semakin rendah variance-nya, semakin
               blur gambarnya (edge-nya lemah).
- Brightness : rata-rata intensitas grayscale. Terlalu gelap atau terlalu
               terang (overexposed) sama-sama dianggap buruk.

`quality_score` dinormalisasi ke rentang 0.0 - 1.0 (1.0 = kualitas terbaik),
supaya bisa langsung dipakai sebagai bobot di ScoreAggregator / ConfidenceEngine.
"""

import cv2
import numpy as np

from app.utils.config import BLUR_THRESHOLD, BRIGHTNESS_MIN, BRIGHTNESS_MAX


class FrameQualityCalculator:

    def __init__(
        self,
        blur_threshold: float = BLUR_THRESHOLD,
        brightness_min: float = BRIGHTNESS_MIN,
        brightness_max: float = BRIGHTNESS_MAX,
        quality_threshold: float = 0.5,
    ):
        self.blur_threshold = blur_threshold
        self.brightness_min = brightness_min
        self.brightness_max = brightness_max
        self.quality_threshold = quality_threshold

    def _blur_score(self, gray, variance: float) -> float:
        # 0 di variance 0, naik linear sampai 1.0 begitu variance >= threshold
        score = variance / self.blur_threshold
        return float(min(1.0, max(0.0, score)))

    def _brightness_score(self, brightness: float) -> float:
        if brightness < self.brightness_min:
            score = brightness / self.brightness_min
        elif brightness > self.brightness_max:
            headroom = 255 - self.brightness_max
            score = 1.0 - ((brightness - self.brightness_max) / headroom)
        else:
            score = 1.0

        return float(min(1.0, max(0.0, score)))

    def compute(self, crop) -> dict:
        """
        Args:
            crop: gambar hasil crop wajah (BGR, hasil dari FaceSelector).

        Returns:
            dict berisi blur_variance, brightness, quality_score (0-1),
            dan is_good (bool, quality_score >= quality_threshold).
        """

        if crop is None or crop.size == 0:
            return {
                "blur_variance": 0.0,
                "brightness": 0.0,
                "quality_score": 0.0,
                "is_good": False,
            }

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop

        blur_variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        brightness = float(np.mean(gray))

        blur_score = self._blur_score(gray, blur_variance)
        brightness_score = self._brightness_score(brightness)

        # Blur sedikit lebih diutamakan daripada brightness karena wajah yang
        # blur membuat prediksi emosi tidak reliable, sementara brightness
        # ringan masih sering tertolong oleh model.
        quality_score = (0.6 * blur_score) + (0.4 * brightness_score)

        return {
            "blur_variance": round(blur_variance, 2),
            "brightness": round(brightness, 2),
            "quality_score": round(quality_score, 3),
            "is_good": quality_score >= self.quality_threshold,
        }
