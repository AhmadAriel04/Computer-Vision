import cv2


EMOTION_COLORS = {
    "happy": (0, 255, 0),
    "neutral": (0, 255, 255),
    "sad": (255, 0, 0),
    "angry": (0, 0, 255),
}


def draw(frame, box, emotion, confidence, counter_code=None):
    color = EMOTION_COLORS.get(str(emotion).lower(), (255, 255, 255))
    x1, y1, x2, y2 = map(int, box)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    label = f"{counter_code + ' | ' if counter_code else ''}{emotion} {confidence:.2f}"
    cv2.putText(
        frame, label, (x1, max(25, y1 - 10)),
        cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2,
    )


def draw_counter_rois(frame, counter_rois):
    height, width = frame.shape[:2]

    for counter_code, config in counter_rois.items():
        customer_roi = config["customer_roi"]
        employee_roi = config.get("employee_roi")

        def rect(roi):
            return (
                int(float(roi["x1"]) * width),
                int(float(roi["y1"]) * height),
                int(float(roi["x2"]) * width),
                int(float(roi["y2"]) * height),
            )

        x1, y1, x2, y2 = rect(customer_roi)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 180, 0), 2)
        cv2.putText(
            frame, f"NASABAH {counter_code}",
            (x1 + 8, max(24, y1 + 24)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 180, 0), 2,
        )

        if employee_roi:
            ex1, ey1, ex2, ey2 = rect(employee_roi)
            cv2.rectangle(frame, (ex1, ey1), (ex2, ey2), (180, 80, 255), 1)
            cv2.putText(
                frame, f"AREA PEGAWAI {counter_code}",
                (ex1 + 8, max(20, ey1 + 20)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 80, 255), 1,
            )
