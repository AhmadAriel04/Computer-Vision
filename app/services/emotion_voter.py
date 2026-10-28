from collections import Counter, deque

# Batas panjang riwayat per wajah agar tidak tumbuh tanpa batas
# selama sesi yang sangat panjang.
MAX_HISTORY = 200


class EmotionVoter:

    def __init__(self, max_history=MAX_HISTORY):

        self.history = {}
        self.max_history = max_history

    def add(self, face_id, emotion):

        self.history.setdefault(
            face_id,
            deque(maxlen=self.max_history)
        ).append(emotion)

    def dominant(self, face_id):

        if face_id not in self.history:

            return "Unknown"

        counter = Counter(
            self.history[face_id]
        )

        return counter.most_common(1)[0][0]

    def clear(self, face_id):

        self.history.pop(
            face_id,
            None
        )