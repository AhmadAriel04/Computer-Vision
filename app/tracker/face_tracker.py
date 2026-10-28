"""
Tracker wajah sederhana berbasis centroid.

Perbaikan dari versi sebelumnya:

1. Pencocokan sekarang satu-ke-satu. Versi lama memakai loop bersarang
   dengan `break` pada kecocokan pertama, sehingga dua deteksi berbeda
   bisa dipetakan ke track ID yang sama dan salah satunya hilang begitu
   saja dari dictionary hasil.

2. Track tidak langsung dibuang saat deteksi meleset. Versi lama
   menimpa `self.faces = updated`, artinya satu frame saja detektor
   gagal melihat wajah, ID langsung hangus dan frame berikutnya
   diberi ID baru. Akibatnya sesi terus terpotong dan riwayat emosi
   ter-reset -- kelihatan berjalan normal di layar, tapi tidak pernah
   terkumpul cukup sampel untuk diskor. Sekarang track bertahan
   sampai TRACK_MAX_LOST frame.

3. Ambang jarak dinormalisasi terhadap lebar kotak wajah, jadi tetap
   masuk akal baik untuk wajah dekat (kotak besar) maupun jauh.
"""

import math

from app.tracker.tracked_face import TrackedFace


def _centroid(box):
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def _distance(box_a, box_b):
    ax, ay = _centroid(box_a)
    bx, by = _centroid(box_b)
    return math.hypot(ax - bx, ay - by)


def _width(box):
    return max(1.0, float(box[2] - box[0]))


class FaceTracker:

    def __init__(self, max_distance_ratio=0.8, max_lost=15):

        self.next_id = 1
        self.faces = {}

        self.max_distance_ratio = max_distance_ratio
        self.max_lost = max_lost

    def update(self, detections):
        """
        Args:
            detections: list kotak (x1, y1, x2, y2)

        Returns:
            dict {face_id: TrackedFace} berisi track yang terlihat
            pada frame ini saja (lost_frames == 0).
        """

        detections = list(detections)

        # --- Bangun semua pasangan kandidat (track, deteksi) ---

        pairs = []

        for face_id, face in self.faces.items():

            for detection_index, box in enumerate(detections):

                distance = _distance(face.box, box)

                # Ambang adaptif: rata-rata lebar kedua kotak
                gate = self.max_distance_ratio * (
                    (_width(face.box) + _width(box)) / 2.0
                )

                if distance <= gate:
                    pairs.append((distance, face_id, detection_index))

        # --- Assignment greedy: pasangan terdekat menang duluan ---

        pairs.sort(key=lambda item: item[0])

        used_tracks = set()
        used_detections = set()
        matches = {}

        for _, face_id, detection_index in pairs:

            if face_id in used_tracks:
                continue

            if detection_index in used_detections:
                continue

            used_tracks.add(face_id)
            used_detections.add(detection_index)

            matches[face_id] = detection_index

        # --- Perbarui track yang cocok ---

        for face_id, detection_index in matches.items():

            face = self.faces[face_id]
            face.box = detections[detection_index]
            face.lost_frames = 0

        # --- Track yang tidak cocok: tambah hitungan hilang ---

        for face_id in list(self.faces.keys()):

            if face_id in matches:
                continue

            face = self.faces[face_id]
            face.lost_frames += 1

            if face.lost_frames > self.max_lost:
                del self.faces[face_id]

        # --- Deteksi baru: buat track baru ---

        for detection_index, box in enumerate(detections):

            if detection_index in used_detections:
                continue

            face_id = self.next_id
            self.next_id += 1

            self.faces[face_id] = TrackedFace(id=face_id, box=box)

        # --- Kembalikan hanya yang benar-benar terlihat ---

        return {
            face_id: face
            for face_id, face in self.faces.items()
            if face.lost_frames == 0
        }

    def reset(self):
        self.faces.clear()
