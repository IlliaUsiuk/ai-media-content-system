from enum import Enum


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


def is_terminal(status: str) -> bool:
    return status in (RunStatus.COMPLETED, RunStatus.FAILED)
