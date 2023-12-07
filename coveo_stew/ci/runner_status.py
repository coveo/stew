from enum import Enum, auto


class RunnerStatus(Enum):
    NotRan = auto()
    Success = auto()
    CheckFailed = auto()
    Error = auto()

    def __str__(self) -> str:
        return str(self.name)  # conversion is redundant, but mypy is confused
