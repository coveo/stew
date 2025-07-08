import time
from dataclasses import dataclass
from typing import Optional

from coveo_stew.ci.checks.lib.base_check import BaseCheck
from coveo_stew.environment import PythonEnvironment


@dataclass
class Task:
    """Represents a single stew ci task (check + environment combination)."""

    check: BaseCheck
    environment: PythonEnvironment
    enable_autofix: bool  # whether to enable autofix for this task; not necessarily the value specified by the user
    purpose: str = "check"  # for logging purposes
    started_at: Optional[float] = None
    ended_at: Optional[float] = None

    @property
    def is_in_progress(self) -> bool:
        return bool(self.started_at and not self.ended_at)

    @property
    def is_complete(self) -> bool:
        return self.ended_at is not None

    @property
    def duration(self) -> float:
        """
        Return the task duration in seconds:
        - If complete: return total duration
        - If in progress: return elapsed time so far
        - If not started: return 0
        """
        if not self.started_at:
            return 0.0
        end_time = self.ended_at or time.time()
        return end_time - self.started_at

    @property
    def name(self) -> str:
        return f"{self.check.name} ({self.purpose})" if self.purpose != "check" else self.check.name

    @property
    def python_version(self) -> str:
        return self.environment.python_version.replace("Python ", "py")

    def starts_now(self) -> None:
        """Mark the task as started at the current time."""
        if self.is_in_progress or self.is_complete:
            raise RuntimeError("Cannot restart Task.")
        self.started_at = time.time()

    def ends_now(self) -> None:
        """Mark the task as ended at the current time."""
        if not self.is_in_progress:
            raise RuntimeError("Cannot end Task that is not in progress.")
        if self.is_complete:
            raise RuntimeError("Task is already complete.")
        self.ended_at = time.time()
