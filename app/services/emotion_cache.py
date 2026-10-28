class EmotionCache:

    def __init__(self):

        self.cache = {}

    def update(
        self,
        face_id,
        emotion,
        confidence
    ):

        self.cache[face_id] = {

            "emotion": emotion,

            "confidence": confidence

        }

    def get(self, face_id):

        return self.cache.get(

            face_id,

            {

                "emotion":"Unknown",

                "confidence":0

            }

        )
    def clear(self, face_id):
        self.cache.pop(
            face_id,
            None
        )