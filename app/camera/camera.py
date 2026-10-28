import cv2

from app.utils.config import CAMERA_INDEX


class Camera:
    """Kamera dengan lifecycle eksplisit: start() dan release()."""

    def __init__(self, index=CAMERA_INDEX):
        self.index = index
        self.cap = None

    def start(self):
        """Membuka kamera hanya saat deteksi akan dimulai."""
        if self.is_opened():
            return True

        self.cap = cv2.VideoCapture(self.index)

        if not self.cap.isOpened():
            self.cap.release()
            self.cap = None
            raise RuntimeError(
                f"Tidak bisa membuka kamera dengan index {self.index}"
            )

        return True

    def is_opened(self):
        return self.cap is not None and self.cap.isOpened()

    def read(self):
        if not self.is_opened():
            return False, None
        return self.cap.read()

    def release(self):
        """Menghentikan kamera dan membebaskan device kamera."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()
