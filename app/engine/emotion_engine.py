class EmotionEngine:

    def __init__(
        self,
        tracker,
        classifier,
        voter,
        cache,
        session
    ):

        self.tracker = tracker
        self.classifier = classifier
        self.voter = voter
        self.cache = cache
        self.session = session