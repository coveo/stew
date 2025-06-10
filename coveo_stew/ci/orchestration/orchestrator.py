import asyncio
import time
from dataclasses import dataclass, field
from typing import Iterable, List, Sequence, TypeVar

from cleo.io.io import IO
from cleo.io.null_io import NullIO
from cleo.io.outputs.output import Verbosity

from coveo_stew.ci.checks.lib.base_check import BaseCheck
from coveo_stew.ci.checks.lib.status import CheckStatus
from coveo_stew.ci.orchestration.matrix import CIMatrix, CIMatrixWorkflowOptions
from coveo_stew.ci.orchestration.results import CheckResults
from coveo_stew.ci.orchestration.task import Task
from coveo_stew.ci.orchestration.ticker_output import TickerOutput
from coveo_stew.environment import PythonEnvironment

T = TypeVar("T")


@dataclass
class CIOrchestrator:
    """Orchestrates the execution of CI tasks across environments."""

    environments: Sequence[PythonEnvironment]
    checks: Sequence[BaseCheck]
    workflow_options: CIMatrixWorkflowOptions = CIMatrixWorkflowOptions.CHECK
    io: IO = NullIO()
    raise_exceptions: bool = False

    # managed internally
    results: List[CheckResults] = field(init=False, default_factory=list)
    _in_progress: List[Task] = field(init=False, default_factory=list)
    _completed: List[Task] = field(init=False, default_factory=list)
    _matrix: CIMatrix = field(init=False)
    _start_time: float = field(init=False)
    _output: TickerOutput = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the matrix and task tracking."""
        if not self.checks:
            raise ValueError("At least one check must be provided.")

        self._start_time = time.time()
        self._output = TickerOutput(io=self.io)
        self._matrix = CIMatrix(environments=self.environments, checks=self.checks)

    @property
    def overall_status(self) -> CheckStatus:
        """Determine the overall status based on completed tasks."""
        return CheckStatus.get_highest_severity(
            [task.check.result.status for task in self._completed]
        )

    async def orchestrate(self) -> CheckStatus:
        """Run all CI tasks in the order determined by the matrix and return the most severe status."""
        self.io.write_line("")
        self.io.write_line(f"🚀 <fg=green>Launching {len(self.checks)} checks</>")

        if not self.checks:  # Early return if no checks
            return CheckStatus.NotRan

        # Show an initial status message
        self._output.show_initial_status()

        if self.workflow_options & CIMatrixWorkflowOptions.SEQUENTIAL:
            self.io.write_line("Running tasks sequentially", verbosity=Verbosity.VERBOSE)
            fn = self._run_tasks_sequentially
        else:
            self.io.write_line("Running tasks in parallel", verbosity=Verbosity.VERBOSE)
            fn = self._run_tasks_in_parallel

        for batch in self._matrix.generate_task_batches(workflow_options=self.workflow_options):
            self.io.write_line("Starting new batch of tasks", verbosity=Verbosity.VERBOSE)
            await fn(batch)

        return self.overall_status

    async def _run_tasks_sequentially(self, ci_tasks: Iterable[Task]) -> None:
        """Run tasks one at a time with status updates, non-blocking."""
        # Convert to list so we can determine when we're on the last task
        task_list = list(ci_tasks)

        # Create a task to update the status line periodically
        status_updater = await self._output.create_status_updater(self._in_progress)

        try:
            for i, task in enumerate(task_list):
                # Display task start
                self._output.display_task_start(task.python_version, task.name)

                # Create and start the task without blocking
                running_task = asyncio.create_task(self._run_task_without_output(task))

                # Wait for task to complete without blocking the event loop
                task, result = await running_task

                # Update task state and display completion
                self._mark_task_completed(task)
                self._output.display_task_completion(task, result.status)

                # Show status line for next task if there is one
                if i < len(task_list) - 1:
                    self._output.update_status_line(self._in_progress)
        finally:
            # Clean up the status updater
            await self._output.cleanup_status_updater(status_updater)

    async def _run_tasks_in_parallel(self, ci_tasks: Iterable[Task]) -> None:
        """Run tasks in parallel with real-time status updates, non-blocking."""
        # Create tasks and add them to asyncio's event loop
        running_tasks = [
            asyncio.create_task(self._run_task_without_output(task)) for task in ci_tasks
        ]

        if not running_tasks:
            return

        # Create a task to update the status line periodically
        status_updater = await self._output.create_status_updater(self._in_progress)

        try:
            # Use a dynamic approach with asyncio.wait to process tasks as they complete
            pending = set(running_tasks)
            while pending:
                try:
                    # Wait for at least one task to complete, but don't block indefinitely
                    done, pending = await asyncio.wait(
                        pending,
                        timeout=0.1,  # Small timeout to keep the loop responsive
                        return_when=asyncio.FIRST_COMPLETED,
                    )

                    # Process completed tasks
                    for completed in done:
                        try:
                            task, result = completed.result()

                            # Update task state and display completion
                            self._mark_task_completed(task)
                            self._output.display_task_completion(task, result.status)

                            # Update the status line with remaining tasks
                            if self._in_progress:
                                self._output.update_status_line(self._in_progress)
                        except asyncio.CancelledError:
                            # Task was cancelled, just skip it
                            continue
                        except Exception as e:
                            # Handle any exceptions from the task
                            self.io.write_line(
                                f"<e>Error processing task result: {str(e)}</e>",
                                verbosity=Verbosity.VERBOSE,
                            )
                except KeyboardInterrupt:
                    # Cancel all pending tasks
                    self.io.write_line("\n<fg=yellow>Cancelling remaining tasks...</>")
                    for pending_task in pending:
                        pending_task.cancel()
                    raise  # Re-raise to be caught by the orchestrator
        finally:
            # Clean up the status updater
            await self._output.cleanup_status_updater(status_updater)

    def _mark_task_completed(self, task: Task) -> None:
        """Mark a task as completed and update internal state."""
        self._completed.append(task)
        self._in_progress.remove(task)

    async def _run_task_without_output(self, task: Task) -> tuple[Task, CheckResults]:
        """Run a task without producing output, for use in parallel execution.

        Returns:
            A tuple of (task, result) for handling by the parallel runner.
        """
        self._in_progress.append(task)
        task_name = (
            f"{task.check.name} ({task.purpose})" if task.purpose != "check" else task.check.name
        )
        task.starts_now()

        try:
            result = await task.check.launch(
                environment=task.environment, auto_fix=task.enable_autofix, task_name=task_name
            )
        except Exception as ex:
            task.ends_now()

            # Create a failed result with the exception
            result = CheckResults(
                name=task_name,
                status=CheckStatus.Error,
                exception=ex,
                duration_seconds=task.duration,
            )
            self.results.append(result)

            if self.raise_exceptions:
                raise
        else:
            # Set the task's duration on the result
            result.duration_seconds = task.duration
            self.results.append(result)
        finally:
            # Record the end time
            # Note: We don't remove from in_progress list here
            # This will be done in the calling method to avoid race conditions
            task.ends_now()

        return task, result
