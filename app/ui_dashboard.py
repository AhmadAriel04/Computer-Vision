import cv2
import time


BG = (10, 14, 22)
PANEL = (18, 24, 34)
PANEL_2 = (22, 29, 41)
BORDER = (45, 57, 74)
TEXT = (225, 232, 242)
MUTED = (130, 145, 165)
ACCENT = (0, 210, 170)
ACCENT_DARK = (0, 90, 75)
WHITE = (245, 248, 252)
RED = (70, 70, 230)
YELLOW = (0, 205, 230)
BLUE = (230, 130, 40)
GREEN = (60, 205, 95)


class DashboardUI:
    """UI dashboard OpenCV tanpa dependency GUI tambahan.

    Mouse:
      - pilih counter saat standby
      - Start Monitoring
      - Stop Monitoring
    Keyboard:
      - S = start
      - ESC = stop
      - Q = keluar
    """

    def __init__(self, window_name, counter_codes):
        self.window_name = window_name
        self.counter_codes = list(counter_codes)
        self.selected_counter = self.counter_codes[0] if self.counter_codes else None
        self.monitoring = False
        self.start_requested = False
        self.stop_requested = False
        self.quit_requested = False
        self.button_rects = {}
        self.counter_rects = {}
        self.last_status = "STANDBY"
        self.status_message = "Pilih pegawai/counter, lalu tekan START MONITORING."
        self.started_at = None
        self.session_count = 0
        self.latest = {}

        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, 1440, 900)
        cv2.setMouseCallback(self.window_name, self._on_mouse)

    @staticmethod
    def _rect(img, xy, fill=None, outline=BORDER, thickness=1, radius=0):
        x1, y1, x2, y2 = map(int, xy)
        if fill is not None:
            cv2.rectangle(img, (x1, y1), (x2, y2), fill, -1)
        if outline is not None:
            cv2.rectangle(img, (x1, y1), (x2, y2), outline, thickness)

    @staticmethod
    def _text(img, text, xy, scale=0.55, color=TEXT, thickness=1):
        cv2.putText(img, str(text), tuple(map(int, xy)), cv2.FONT_HERSHEY_SIMPLEX,
                    scale, color, thickness, cv2.LINE_AA)

    def _on_mouse(self, event, x, y, flags, param):
        if event != cv2.EVENT_LBUTTONUP:
            return

        if not self.monitoring:
            for code, rect in self.counter_rects.items():
                if self._inside(x, y, rect):
                    self.selected_counter = code
                    self.status_message = f"Counter {code} dipilih. Tekan START MONITORING."
                    return

            if self._inside(x, y, self.button_rects.get("start")):
                if self.selected_counter:
                    self.start_requested = True
                return

        if self._inside(x, y, self.button_rects.get("stop")):
            self.stop_requested = True

        if self._inside(x, y, self.button_rects.get("quit")):
            self.quit_requested = True

    @staticmethod
    def _inside(x, y, rect):
        if not rect:
            return False
        x1, y1, x2, y2 = rect
        return x1 <= x <= x2 and y1 <= y <= y2

    def request_start(self):
        self.start_requested = True

    def request_stop(self):
        self.stop_requested = True

    def consume_start(self):
        value = self.start_requested
        self.start_requested = False
        return value

    def consume_stop(self):
        value = self.stop_requested
        self.stop_requested = False
        return value

    def set_monitoring(self, value, message=None):
        self.monitoring = bool(value)
        self.last_status = "MONITORING ACTIVE" if value else "STANDBY"
        if value:
            self.started_at = time.time()
        else:
            self.started_at = None
        if message:
            self.status_message = message

    def set_latest(self, counter_code, emotion="Unknown", confidence=0.0,
                   samples=0, duration=0.0, status="WAITING"):
        self.latest[counter_code] = {
            "emotion": str(emotion).lower(),
            "confidence": float(confidence),
            "samples": int(samples),
            "duration": float(duration),
            "status": status,
        }

    def set_session_count(self, count):
        self.session_count = int(count)

    def _role(self, code):
        code = str(code).upper()
        if code.startswith("CS"):
            return "Customer Service"
        if code.startswith("TL"):
            return "Teller"
        if code.startswith("SEC"):
            return "Security"
        return "Pegawai Pelayanan"

    def _emotion_color(self, emotion):
        return {
            "happy": GREEN,
            "neutral": (180, 185, 195),
            "sad": BLUE,
            "angry": RED,
        }.get(str(emotion).lower(), MUTED)

    def _draw_header(self, canvas):
        self._rect(canvas, (0, 0, canvas.shape[1], 62), fill=(8, 11, 18), outline=None)
        self._text(canvas, "FACEEVISTION MONITOR", (24, 29), 0.62, ACCENT, 2)
        self._text(canvas, "Bank Expression Analytics", (24, 49), 0.34, MUTED, 1)
        self._text(canvas, "Computer Vision untuk Deteksi Wajah", (canvas.shape[1] // 2 - 135, 36),
                   0.48, WHITE, 1)
        status = self.last_status
        color = ACCENT if self.monitoring else MUTED
        self._rect(canvas, (canvas.shape[1] - 160, 18, canvas.shape[1] - 24, 45),
                   fill=PANEL_2, outline=BORDER)
        self._text(canvas, "●  " + status, (canvas.shape[1] - 146, 36), 0.40, color, 1)

    def _draw_camera_panel(self, canvas, frame):
        x, y, w, h = 18, 82, int(canvas.shape[1] * 0.64), canvas.shape[0] - 168
        self._rect(canvas, (x, y, x + w, y + h), fill=(11, 17, 26), outline=BORDER)

        if frame is None:
            self._text(canvas, "CAMERA STANDBY", (x + w // 2 - 78, y + h // 2), 0.62, MUTED, 1)
            self._text(canvas, "Pilih counter kemudian START MONITORING", (x + w // 2 - 180, y + h // 2 + 30),
                       0.40, MUTED, 1)
        else:
            resized = cv2.resize(frame, (w - 2, h - 2), interpolation=cv2.INTER_AREA)
            canvas[y + 1:y + h - 1, x + 1:x + w - 1] = resized

        self._text(canvas, f"CAM-01  |  1080p  |  30 FPS", (x + 12, y + 22), 0.35, MUTED, 1)
        self._text(canvas, f"COUNTER: {self.selected_counter or '-'}", (x + 12, y + h - 12), 0.38, ACCENT, 1)
        return (x, y, w, h)

    def _draw_right_panel(self, canvas):
        x = int(canvas.shape[1] * 0.64) + 34
        right = canvas.shape[1] - 18
        width = right - x

        self._text(canvas, "ACTIVE EMPLOYEE", (x, 100), 0.35, MUTED, 1)
        self.counter_rects = {}
        card_y = 112
        card_h = 58
        gap = 8
        for code in self.counter_codes:
            selected = code == self.selected_counter
            rect = (x, card_y, right, card_y + card_h)
            self.counter_rects[code] = rect
            fill = (16, 42, 40) if selected else PANEL
            outline = ACCENT if selected else BORDER
            self._rect(canvas, rect, fill=fill, outline=outline)
            badge = code.split("-")[0][:3]
            self._rect(canvas, (x + 10, card_y + 10, x + 45, card_y + 45), fill=ACCENT_DARK if selected else PANEL_2, outline=None)
            self._text(canvas, badge, (x + 17, card_y + 32), 0.34, ACCENT if selected else MUTED, 1)
            self._text(canvas, code, (x + 58, card_y + 24), 0.48, WHITE, 1)
            self._text(canvas, self._role(code), (x + 58, card_y + 42), 0.30, MUTED, 1)
            info = self.latest.get(code, {})
            self._text(canvas, info.get("status", "READY"), (right - 90, card_y + 33), 0.30,
                       ACCENT if info.get("status") == "ACTIVE" else MUTED, 1)
            card_y += card_h + gap

        top = card_y + 8
        self._text(canvas, f"EXPRESSION ANALYSIS — {self.selected_counter or '-'}", (x, top + 8), 0.34, MUTED, 1)
        top += 22
        info = self.latest.get(self.selected_counter, {}) if self.selected_counter else {}
        emotion = info.get("emotion", "Unknown")
        confidence = info.get("confidence", 0.0)
        samples = info.get("samples", 0)
        duration = info.get("duration", 0.0)
        col_w = (width - 8) // 2
        emotions = ["happy", "neutral", "sad", "angry"]
        for idx, emo in enumerate(emotions):
            col = idx % 2
            row = idx // 2
            bx = x + col * (col_w + 8)
            by = top + row * 68
            active = emotion == emo
            self._rect(canvas, (bx, by, bx + col_w, by + 58), fill=(15, 31, 27) if active else PANEL,
                       outline=self._emotion_color(emo) if active else BORDER)
            self._text(canvas, emo.upper(), (bx + 10, by + 20), 0.30, self._emotion_color(emo), 1)
            value = confidence * 100 if active else 0
            self._text(canvas, f"{value:.0f}%", (bx + 10, by + 43), 0.55, WHITE, 1)
            self._rect(canvas, (bx + 75, by + 38, bx + col_w - 10, by + 43), fill=(35, 44, 55), outline=None)
            if value > 0:
                self._rect(canvas, (bx + 75, by + 38, bx + 75 + int((col_w - 85) * value / 100), by + 43),
                           fill=self._emotion_color(emo), outline=None)

        stats_y = top + 150
        self._text(canvas, f"SAMPLES   {samples:03d}", (x, stats_y), 0.34, MUTED, 1)
        self._text(canvas, f"DURASI    {duration:05.1f}s", (x + 150, stats_y), 0.34, MUTED, 1)
        self._text(canvas, f"DOMINANT  {emotion.upper()}", (x, stats_y + 23), 0.34, self._emotion_color(emotion), 1)
        self._text(canvas, f"SESSIONS  {self.session_count:03d}", (x + 150, stats_y + 23), 0.34, MUTED, 1)

    def render(self, frame=None):
        canvas = __import__('numpy').zeros((900, 1440, 3), dtype='uint8')
        canvas[:] = BG
        self._draw_header(canvas)
        self._draw_camera_panel(canvas, frame)
        self._draw_right_panel(canvas)

        y = canvas.shape[0] - 66
        self.button_rects = {}
        if self.monitoring:
            self._rect(canvas, (18, y, canvas.shape[1] - 165, y + 42), fill=(8, 55, 48), outline=ACCENT)
            self._text(canvas, "■  STOP MONITORING", (canvas.shape[1] // 2 - 85, y + 27), 0.50, ACCENT, 2)
            self.button_rects["stop"] = (18, y, canvas.shape[1] - 165, y + 42)
        else:
            self._rect(canvas, (18, y, canvas.shape[1] - 165, y + 42), fill=(8, 55, 48), outline=ACCENT)
            self._text(canvas, "▶  START MONITORING", (canvas.shape[1] // 2 - 95, y + 27), 0.50, ACCENT, 2)
            self.button_rects["start"] = (18, y, canvas.shape[1] - 165, y + 42)

        self._rect(canvas, (canvas.shape[1] - 145, y, canvas.shape[1] - 18, y + 42), fill=PANEL, outline=BORDER)
        self._text(canvas, "RESET", (canvas.shape[1] - 112, y + 27), 0.44, MUTED, 1)
        self.button_rects["quit"] = (canvas.shape[1] - 145, y, canvas.shape[1] - 18, y + 42)

        self._text(canvas, self.status_message, (22, canvas.shape[0] - 82), 0.32, MUTED, 1)
        cv2.imshow(self.window_name, canvas)
        return cv2.waitKey(30) & 0xFF
