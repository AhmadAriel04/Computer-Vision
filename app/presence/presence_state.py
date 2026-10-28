from enum import Enum


class PresenceState(Enum):
    WAITING = "waiting"
    PRESENT = "present"
    ABSENT = "absent"