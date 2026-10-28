"""Pemilihan wajah NASABAH berdasarkan ROI counter.

Prinsip:
1. Setiap counter memiliki customer_roi.
2. Wajah harus berada di customer_roi.
3. Jika employee_roi dikonfigurasi, wajah di area tersebut dikecualikan.
4. Satu wajah hanya boleh dipakai oleh satu counter pada satu frame.
5. Jika beberapa wajah berada di satu counter, kandidat terbesar dipilih.

Model ini tidak mengenali identitas seseorang sebagai pegawai/nasabah.
Karena itu ROI kamera wajib diarahkan dengan benar ke area nasabah.
"""


class FaceSelector:

    @staticmethod
    def _center(box):
        x1, y1, x2, y2 = box
        return (float(x1 + x2) / 2.0, float(y1 + y2) / 2.0)

    @staticmethod
    def _area(box):
        x1, y1, x2, y2 = box
        return max(0.0, x2 - x1) * max(0.0, y2 - y1)

    @staticmethod
    def _inside_roi(box, roi, width, height):
        if not roi:
            return False

        cx, cy = FaceSelector._center(box)
        x1 = float(roi["x1"]) * width
        y1 = float(roi["y1"]) * height
        x2 = float(roi["x2"]) * width
        y2 = float(roi["y2"]) * height

        return x1 <= cx <= x2 and y1 <= cy <= y2

    @staticmethod
    def _roi_center_distance(box, roi, width, height):
        cx, cy = FaceSelector._center(box)
        rx = ((float(roi["x1"]) + float(roi["x2"])) / 2.0) * width
        ry = ((float(roi["y1"]) + float(roi["y2"])) / 2.0) * height
        return ((cx - rx) / max(width, 1)) ** 2 + ((cy - ry) / max(height, 1)) ** 2

    def select_by_counters(self, tracked_faces, frame_shape, counter_rois):
        if not tracked_faces:
            return {}

        height, width = frame_shape[:2]
        candidates = []

        # Cari semua pasangan face-counter yang valid.
        for face_id, face in tracked_faces.items():
            for counter_code, config in counter_rois.items():
                customer_roi = config["customer_roi"]
                employee_roi = config.get("employee_roi")

                if not self._inside_roi(face.box, customer_roi, width, height):
                    continue

                # Optional exclusion zone untuk area pegawai.
                if employee_roi and self._inside_roi(
                    face.box, employee_roi, width, height
                ):
                    continue

                distance = self._roi_center_distance(
                    face.box, customer_roi, width, height
                )

                candidates.append((distance, -self._area(face.box), face_id, counter_code))

        # Satu wajah tidak boleh menghasilkan dua session counter.
        candidates.sort()
        used_faces = set()
        used_counters = set()
        selected = {}

        for _, _, face_id, counter_code in candidates:
            if face_id in used_faces or counter_code in used_counters:
                continue

            selected[counter_code] = tracked_faces[face_id]
            used_faces.add(face_id)
            used_counters.add(counter_code)

        return selected

    # Kompatibilitas kode lama.
    def select(self, tracked_faces):
        if not tracked_faces:
            return None
        return max(tracked_faces.values(), key=lambda face: self._area(face.box))
