import time

from app.presence.presence_state import PresenceState


class FacePresenceDetector:

    def __init__(
        self,
        min_presence=2.0,
        max_absence=3.0
    ):

        self.min_presence = min_presence
        self.max_absence = max_absence

        self.faces = {}

    def update(self, face_id):

        now = time.time()

        if face_id not in self.faces:

            self.faces[face_id] = {
                "first_seen": now,
                "last_seen": now,
                "active": False
            }

            return PresenceState.WAITING

        face = self.faces[face_id]

        face["last_seen"] = now

        if not face["active"]:

            duration = now - face["first_seen"]

            if duration >= self.min_presence:

                face["active"] = True

                return PresenceState.PRESENT

            return PresenceState.WAITING

        return PresenceState.PRESENT
    
    def cleanup(self):

        now = time.time()

        removed = []

        for face_id, face in list(self.faces.items()):

            if now - face["last_seen"] > self.max_absence:

                removed.append(face_id)

                del self.faces[face_id]

        return removed