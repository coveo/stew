from enum import Enum, auto
from typing import TypeVar

T = TypeVar("T")


class CheckStatus(Enum):
    NotRan = auto()
    Success = auto()
    CheckFailed = auto()
    Error = auto()
    Cancelled = auto()

    def __str__(self) -> str:
        return str(self.name)  # conversion is redundant, but mypy is confused

    def colored(self) -> str:
        """Return a colored representation of the status."""
        return f"<fg={check_status_color_map[self]}>{self.name}</fg>"

    def emoji(self) -> str:
        """Return an emoji representation of the status."""
        return check_status_emoji_map.get(self)

    @classmethod
    def get_highest_severity(cls, statuses: list["CheckStatus"]) -> "CheckStatus":
        """Return the status with the highest severity from a list of statuses."""
        if not statuses:
            return cls.NotRan

        for status in (cls.Error, cls.CheckFailed, cls.Cancelled, cls.Success):
            if status in statuses:
                return status

        return cls.NotRan


check_status_color_map = {
    CheckStatus.NotRan: "light_gray",
    CheckStatus.Success: "green",
    CheckStatus.CheckFailed: "yellow",
    CheckStatus.Error: "red",
    CheckStatus.Cancelled: "blue",
}

check_status_emoji_map = {
    CheckStatus.Success: "✔️",
    CheckStatus.CheckFailed: "🤖",
    CheckStatus.Error: "💥",
    CheckStatus.NotRan: "❔",
    CheckStatus.Cancelled: "🛑",
}
