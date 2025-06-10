"""Matrix-related classes for CI execution organization."""

from dataclasses import dataclass
from enum import IntFlag
from typing import Generator, Iterable, Sequence

from coveo_stew.ci.checks.lib.base_check import BaseCheck
from coveo_stew.ci.orchestration.task import Task
from coveo_stew.environment import PythonEnvironment


class CIMatrixWorkflowOptions(IntFlag):
    """Defines the workflow options for CI matrix execution."""

    NONE = 0
    CHECK = 1 << 0  # Run check tasks
    AUTOFIX = 1 << 1  # Run autofix tasks
    SEQUENTIAL = 1 << 2  # Run tasks sequentially (default is parallel execution)


@dataclass
class CIMatrix:
    """
    Manages the execution order of tasks across multiple environments.
    At least one environment and one check are required.
    """

    environments: Sequence[PythonEnvironment]
    checks: Sequence[BaseCheck]

    def __post_init__(self) -> None:
        if not self.environments:
            raise ValueError("At least one environment is required")
        if not self.checks:
            raise ValueError("At least one check is required")

    def _create_autofix_tasks(self) -> Generator[Task, None, None]:
        """Create autofix tasks for checks that support it, using the first environment."""
        return (
            Task(
                check=check,
                environment=self.environments[0],  # Use first env for autofix
                enable_autofix=True,
                purpose="autofix",
            )
            for check in self.checks
            if check.supports_auto_fix
        )

    def _create_check_tasks(self) -> Generator[Task, None, None]:
        """Create check tasks for all checks/environment combinations."""
        return (
            Task(check=check, environment=env, enable_autofix=False, purpose="check")
            for env in self.environments
            for check in self.checks
        )

    def generate_task_batches(
        self, workflow_options: CIMatrixWorkflowOptions
    ) -> Generator[Iterable[Task], None, None]:
        """Yields batches of tasks in the correct execution order based on the workflow flags."""
        if workflow_options == CIMatrixWorkflowOptions.NONE:
            raise ValueError("At least one workflow flag must be set")

        # AUTOFIX tasks must run first since they modify files
        if workflow_options & CIMatrixWorkflowOptions.AUTOFIX:
            for task in self._create_autofix_tasks():
                yield [task]

        # Only yield check tasks if the CHECK flag is set
        if workflow_options & CIMatrixWorkflowOptions.CHECK:
            yield self._create_check_tasks()
