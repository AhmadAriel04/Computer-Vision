import time
import uuid
from datetime import datetime, timezone


class SessionManager:
    """Mengelola session per kombinasi counter + face tracker ID."""

    def __init__(self, min_presence=2.0, max_absence=4.0):
        self.min_presence = float(min_presence)
        self.max_absence = float(max_absence)
        self.sessions = {}          # session_key -> session data
        self.presence = {}          # session_key -> presence data
        self.face_to_session = {}   # face_id -> active session_key
        self.finished_queue = []

    def _new_uid(self):
        now = time.time()
        return (
            "CV-"
            + datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y%m%d-%H%M%S")
            + "-"
            + uuid.uuid4().hex[:8].upper()
        )

    def update_presence(self, session_key, face_id, counter_code):
        now = time.time()

        # Jika tracker ID yang sama berpindah counter, tutup session lama.
        previous_key = self.face_to_session.get(face_id)
        if previous_key and previous_key != session_key:
            previous = self.presence.get(previous_key)
            if previous and previous.get("active"):
                self.finish(previous_key)
                self.finished_queue.append(previous_key)
            self.presence.pop(previous_key, None)

        self.face_to_session[face_id] = session_key

        if session_key not in self.presence:
            self.presence[session_key] = {
                "first_seen": now,
                "last_seen": now,
                "active": False,
                "face_id": face_id,
                "counter_code": counter_code,
            }
            return False

        state = self.presence[session_key]
        state["last_seen"] = now
        state["face_id"] = face_id
        state["counter_code"] = counter_code

        if state["active"]:
            return True

        if now - state["first_seen"] >= self.min_presence:
            state["active"] = True
            self.start(session_key, face_id, counter_code)
            return True

        return False

    def start(self, session_key, face_id, counter_code):
        if session_key in self.sessions:
            return

        now = time.time()
        self.sessions[session_key] = {
            "session_uid": self._new_uid(),
            "face_id": face_id,
            "counter_code": counter_code,
            "start": now,
            "end": None,
            "finished": False,
            "frames_seen": 0,
        }

        print(
            f"[SessionManager] Session dimulai | face_id={face_id} | "
            f"counter={counter_code} | session_uid={self.sessions[session_key]['session_uid']}"
        )

    def finish(self, session_key):
        data = self.sessions.get(session_key)
        if data is None or data["finished"]:
            return

        data["end"] = time.time()
        data["finished"] = True
        print(
            f"[SessionManager] Session selesai | face_id={data['face_id']} | "
            f"counter={data['counter_code']} | session_uid={data['session_uid']}"
        )

    def cleanup(self):
        now = time.time()
        removed = []

        for session_key in list(self.presence.keys()):
            state = self.presence[session_key]
            if now - state["last_seen"] <= self.max_absence:
                continue

            if state["active"]:
                self.finish(session_key)
                removed.append(session_key)
            else:
                # Presence belum pernah mencapai 2 detik.
                self.presence.pop(session_key, None)
                face_id = state.get("face_id")
                if self.face_to_session.get(face_id) == session_key:
                    self.face_to_session.pop(face_id, None)

        return removed

    def finish_all(self):
        """Menutup semua session aktif, dipakai saat ESC/stop."""
        finished = []
        for session_key in list(self.sessions.keys()):
            data = self.sessions[session_key]
            if not data["finished"]:
                self.finish(session_key)
                finished.append(session_key)
        return finished

    def drain_finished(self):
        items = list(dict.fromkeys(self.finished_queue))
        self.finished_queue.clear()
        return items

    def increment_frame(self, session_key):
        data = self.sessions.get(session_key)
        if data and not data["finished"]:
            data["frames_seen"] += 1

    def duration(self, session_key):
        data = self.sessions.get(session_key)
        if not data:
            return 0.0
        end = data["end"] or time.time()
        return round(end - data["start"], 2)

    def get_session_uid(self, session_key):
        data = self.sessions.get(session_key)
        return data.get("session_uid") if data else None

    def get_frames_seen(self, session_key):
        data = self.sessions.get(session_key)
        return int(data.get("frames_seen", 0)) if data else 0

    def get_counter_code(self, session_key):
        data = self.sessions.get(session_key)
        return data.get("counter_code") if data else None

    def get_face_id(self, session_key):
        data = self.sessions.get(session_key)
        return data.get("face_id") if data else None

    def timestamps(self, session_key):
        data = self.sessions.get(session_key)
        if not data:
            return {"started_at": None, "ended_at": None}

        def iso(ts):
            return (
                datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
                if ts is not None else None
            )

        return {"started_at": iso(data["start"]), "ended_at": iso(data["end"])}

    def is_active(self, session_key):
        state = self.presence.get(session_key)
        return bool(state and state["active"])

    def remove(self, session_key):
        data = self.sessions.pop(session_key, None)
        self.presence.pop(session_key, None)

        if data:
            face_id = data.get("face_id")
            if self.face_to_session.get(face_id) == session_key:
                self.face_to_session.pop(face_id, None)

        self.finished_queue = [k for k in self.finished_queue if k != session_key]
