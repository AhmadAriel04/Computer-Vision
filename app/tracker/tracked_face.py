from dataclasses import dataclass

@dataclass
class TrackedFace:

    id: int

    box: tuple

    emotion: str = "Unknown"

    confidence: float = 0.0

    lost_frames: int = 0