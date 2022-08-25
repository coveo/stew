from enum import Enum, auto


class RunnerStatus(Enum):
    NotRan = auto()
    Success = auto()
    CheckFailed = auto()
    Error = auto()

    def __str__(self) -> str:
        return self.name
