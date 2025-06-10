"""Console output handling for the CI orchestrator with animated tickers."""

import asyncio
import time
from typing import List

from cleo.io.io import IO
from cleo.io.null_io import NullIO

from coveo_stew.ci.checks.lib.status import CheckStatus
from coveo_stew.ci.orchestration.output import OutputHandler
from coveo_stew.ci.orchestration.task import Task


class TickerOutput(OutputHandler):
    """Handles console output with animated status lines for CI tasks."""

    def __init__(self, io: IO = NullIO()):
        """Initialize the ticker output handler.

        Args:
            io: The IO interface for writing output
        """
        super().__init__(io)
        self._status_line_visible: bool = False
        self._ticker_frames: List[str] = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._status_update_interval: float = 1 / len(self._ticker_frames)

    def get_ticker_frame(self) -> str:
        """Get the current ticker frame based on elapsed time."""
        elapsed_seconds = time.time() - self._start_time
        frame_index = int(elapsed_seconds * 8) % len(self._ticker_frames)
        return self._ticker_frames[frame_index]

    def show_initial_status(self) -> None:
        """Display an initial status message when orchestration starts."""
        ticker = self.get_ticker_frame()
        self.io.write(f" {ticker} [0s] Preparing to run checks...")
        self._status_line_visible = True

    def get_status_line(self, in_progress: List[Task]) -> str:
        """Format a status line showing all currently running tasks with overall duration.

        Args:
            in_progress: List of currently running tasks

        Returns:
            Formatted status line string
        """
        if not in_progress:
            return ""

        # Get the current ticker frame
        ticker = self.get_ticker_frame()

        # Calculate overall duration since started
        current_time = time.time()
        overall_duration = current_time - self._start_time
        # Round to lowest second to avoid rapid fluctuation with high refresh rate
        overall_duration_seconds = int(overall_duration)

        # Format the list of running tasks
        running_tasks = []
        for task in in_progress:
            task_name = task.check.name
            if task.purpose != "check":
                task_name += f" ({task.purpose})"
            python_version = task.environment.python_version.replace("Python ", "py")
            running_tasks.append(f"{python_version}:{task_name}")

        status_line = f" {ticker} [{overall_duration_seconds}s] Running: {', '.join(running_tasks)}"

        # Truncate if too long
        max_length = 100  # Adjust based on typical terminal width
        if len(status_line) > max_length:
            status_line = status_line[: max_length - 3] + "..."

        return status_line

    def update_status_line(self, in_progress: List[Task]) -> None:
        """Update the status line showing current running tasks.

        Args:
            in_progress: List of currently running tasks
        """
        status_line = self.get_status_line(in_progress)

        if not status_line and self._status_line_visible:
            # Clear the status line if there are no running tasks
            self.io.overwrite("")
            self._status_line_visible = False
            return

        if status_line:
            # Always overwrite to ensure previous content is cleared
            self.io.overwrite(status_line)
            self._status_line_visible = True

    def clear_status_line(self) -> None:
        """Clear the status line if it's visible."""
        if self._status_line_visible:
            self.io.overwrite("")
            self._status_line_visible = False

    def display_task_start(self, python_version_name: str, task_name: str) -> None:
        """Display the task start message with paw emoji.

        Args:
            python_version_name: Formatted Python version name
            task_name: Name of the task being started
        """
        # Clear any status line before showing task start
        self.clear_status_line()
        self.io.write_line(f" 🐾  <fg=light_gray>{python_version_name} -> {task_name}</>")

    def display_task_completion(self, task: Task, status: CheckStatus) -> None:
        """Display task completion message.

        Args:
            task: The completed task
        """
        duration = task.duration

        # Clear status line before writing completion message
        self.clear_status_line()
        self.io.write_line(
            f" {status.emoji()}  {task.python_version} -> {task.name}: {duration:.1f}s"
        )

    async def status_update_loop(self, in_progress: List[Task]) -> None:
        """Periodically update the status line showing running tasks.

        Args:
            in_progress: A reference to the list of in-progress tasks
        """
        try:
            while True:
                self.update_status_line(in_progress)
                await asyncio.sleep(self._status_update_interval)
        except asyncio.CancelledError:
            pass  # Expected when the parent task completes

    async def create_status_updater(self, in_progress: List[Task]) -> asyncio.Task:
        """Create and return a status line updater task.

        Args:
            in_progress: A reference to the list of in-progress tasks

        Returns:
            Asyncio task that updates status line
        """
        return asyncio.create_task(self.status_update_loop(in_progress))

    async def cleanup_status_updater(self, status_updater: asyncio.Task) -> None:
        """Cancel and clean up the status updater task.

        Args:
            status_updater: The task to clean up
        """
        status_updater.cancel()
        try:
            await status_updater
        except asyncio.CancelledError:
            pass

        # Clear status line at the end if needed
        self.clear_status_line()
