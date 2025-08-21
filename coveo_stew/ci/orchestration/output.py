"""Base output handling for the CI orchestrator."""

import time
from typing import Any, List

from cleo.io.io import IO
from cleo.io.null_io import NullIO

from coveo_stew.ci.checks.lib.status import CheckStatus
from coveo_stew.ci.orchestration.task import Task


class OutputHandler:
    """Base class for CI task output handling."""

    def __init__(self, io: IO = NullIO()):
        """Initialize the output handler.

        Args:
            io: The IO interface for writing output
        """
        self.io = io
        self._start_time: float = time.time()

    def display_task_start(self, python_version_name: str, task_name: str) -> None:
        """Display a task start message.

        Args:
            python_version_name: Formatted Python version name
            task_name: Name of the task being started
        """
        raise NotImplementedError("Subclasses must implement display_task_start")

    def display_task_completion(self, task: Task, status: CheckStatus) -> None:
        """Display a task completion message.

        Args:
            task: The completed task
        """
        raise NotImplementedError("Subclasses must implement display_task_completion")

    def show_initial_status(self) -> None:
        """Display an initial status message when the orchestration starts."""
        # Default implementation does nothing

    def update_status_line(self, in_progress: List[Task]) -> None:
        """Update the status line showing currently running tasks.

        Args:
            in_progress: List of currently running tasks
        """
        # Default implementation does nothing

    async def create_status_updater(self, in_progress: List[Task]) -> Any:
        """Create a status updater for tracking task progress.

        Args:
            in_progress: A reference to the list of in-progress tasks

        Returns:
            An object representing the status updater, or None if not applicable
        """
        # Default implementation does nothing
        return None

    async def cleanup_status_updater(self, status_updater: Any) -> None:
        """Clean up the status updater.

        Args:
            status_updater: The updater object to clean up
        """
        # Default implementation does nothing
