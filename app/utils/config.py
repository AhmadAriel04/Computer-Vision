import json
import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

FACE_MODEL = BASE_DIR / "models" / "yolo11n-pose_widerface.pt"
EMOTION_MODEL = BASE_DIR / "models" / "best.pt"

CAMERA_INDEX = int(os.getenv("CV_CAMERA_INDEX", "0"))

FACE_CONF = 0.45
FACE_IOU = 0.45
EMOTION_CONF = 0.70
EMOTION_INTERVAL = 5
WINDOW_NAME = "BSI Emotion Recognition"

BLUR_THRESHOLD = 100.0
BRIGHTNESS_MIN = 40.0
BRIGHTNESS_MAX = 220.0

MIN_RELIABLE_SAMPLES = 5
MIN_RELIABLE_DURATION = 3.0

API_BASE_URL = os.getenv("CV_API_BASE_URL", "http://localhost:8001")
API_ENDPOINT = "/api/cv/sessions"
API_TOKEN = os.getenv("CV_API_TOKEN", "")
API_TIMEOUT = 10.0
API_MAX_RETRIES = 2
MODEL_VERSION = os.getenv("CV_MODEL_VERSION", "emotion-v1")

# ------------------------------------------------------------------
# MULTI-COUNTER
# ------------------------------------------------------------------
# Format lama tetap didukung:
# {"CS-01":{"x1":0,"y1":0,"x2":0.5,"y2":1}}
# Format baru direkomendasikan:
# {
#   "CS-01": {
#     "customer_roi": {"x1":0,"y1":0,"x2":0.5,"y2":1},
#     "employee_roi": {"x1":0,"y1":0,"x2":0.5,"y2":0.35}
#   },
#   "TL-01": {...}
# }

DEFAULT_COUNTER_ROIS = {
    "CS-01": {
        "customer_roi": {
            "x1": 0.00,
            "y1": 0.35,
            "x2": 0.50,
            "y2": 1.00,
        },
        "employee_roi": None,
    },
    "TL-01": {
        "customer_roi": {
            "x1": 0.50,
            "y1": 0.35,
            "x2": 1.00,
            "y2": 1.00,
        },
        "employee_roi": None,
    },
}


def _valid_roi(roi):
    if not isinstance(roi, dict):
        return False

    try:
        values = [float(roi[k]) for k in ("x1", "y1", "x2", "y2")]
    except (KeyError, TypeError, ValueError):
        return False

    x1, y1, x2, y2 = values
    return (
        0.0 <= x1 < x2 <= 1.0
        and 0.0 <= y1 < y2 <= 1.0
    )


def _normalize_counter_config(code, config):
    # Format baru.
    if isinstance(config, dict) and "customer_roi" in config:
        customer_roi = config.get("customer_roi")
        employee_roi = config.get("employee_roi")
    else:
        # Format lama: konfigurasi langsung dianggap customer ROI.
        customer_roi = config
        employee_roi = None

    if not _valid_roi(customer_roi):
        return None

    if employee_roi is not None and not _valid_roi(employee_roi):
        employee_roi = None

    return {
        "customer_roi": {
            key: float(customer_roi[key])
            for key in ("x1", "y1", "x2", "y2")
        },
        "employee_roi": (
            {
                key: float(employee_roi[key])
                for key in ("x1", "y1", "x2", "y2")
            }
            if employee_roi is not None
            else None
        ),
    }


raw_rois = os.getenv("CV_COUNTER_ROIS", "").strip()

if raw_rois:
    try:
        parsed_rois = json.loads(raw_rois)
    except json.JSONDecodeError:
        print("[Config] CV_COUNTER_ROIS tidak valid. Menggunakan default.")
        parsed_rois = DEFAULT_COUNTER_ROIS
else:
    parsed_rois = DEFAULT_COUNTER_ROIS

if not isinstance(parsed_rois, dict):
    parsed_rois = DEFAULT_COUNTER_ROIS

COUNTER_ROIS = {}
for counter_code, counter_config in parsed_rois.items():
    normalized = _normalize_counter_config(counter_code, counter_config)
    if normalized:
        COUNTER_ROIS[str(counter_code)] = normalized

if not COUNTER_ROIS:
    raise RuntimeError(
        "Tidak ada COUNTER_ROIS yang valid. "
        "Atur CV_COUNTER_ROIS di .env."
    )
