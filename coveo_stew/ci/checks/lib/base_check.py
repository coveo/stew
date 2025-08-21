from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Any, List, Protocol

from cleo.io.io import IO

from coveo_stew.ci.checks.lib.status import CheckStatus
from coveo_stew.ci.orchestration.results import CheckResults
from coveo_stew.ci.reporting.reporting import generate_report
from coveo_stew.environment import PythonEnvironment
from coveo_stew.stew import PythonProject


class CheckFunction(Protocol):
    """Interface for calling routines in CI checks."""

    async def __call__(self, environment: PythonEnvironment, **kwargs: Any) -> CheckStatus: ...


class BaseCheck(metaclass=ABCMeta):
    """Base class for all checks. Handles result collection and reporting."""

    name: str  # must be set by subclasses to provide a friendly name for the check.
    supports_auto_fix: bool = False  # set to True if the check supports autofix.
    outputs_own_report: bool = False  # set to True if the check produces its own report.

    def __init__(self, io: IO, *, _pyproject: PythonProject) -> None:
        assert self.name, "Check name must be set in the subclass"
        self._results: List[CheckResults] = []
        self._io = io
        self._pyproject = _pyproject

    @property
    def project(self) -> PythonProject:
        return self._pyproject

    @property
    def io(self) -> IO:
        return self._io

    @property
    def result(self) -> CheckResults:
        """Access to the most recent check result."""
        if self._results:
            return self._results[-1]
        raise ValueError("No results available")

    async def launch(
        self,
        task_name: str,
        environment: PythonEnvironment = None,
        auto_fix: bool = False,
    ) -> CheckResults:
        """Launch the check and collect the result."""
        result = CheckResults(name=task_name, environment=environment)
        self._results.append(result)

        fn = self._do_autofix if auto_fix and self.supports_auto_fix else self._do_check

        try:
            # noinspection PyTypeChecker
            result.status = await self._execute_check_function(fn, environment)
        except Exception as e:
            result.exception = e
            result.status = CheckStatus.Error
            raise

        if not self.outputs_own_report:
            self._output_generic_report()

        return result

    async def _execute_check_function(
        self,
        fn: CheckFunction,
        environment: PythonEnvironment,
    ) -> CheckStatus:
        """isolated check execution to simplify mocking"""
        return await fn(environment)

    @abstractmethod
    async def _do_check(self, environment: PythonEnvironment, **kwargs: Any) -> CheckStatus:
        """Implementations define their check mechanism here."""

    async def _do_autofix(self, environment: PythonEnvironment, **kwargs: Any) -> CheckStatus:
        """Implementations define their autofix mechanism here."""
        return CheckStatus.NotRan

    def report_path(self, result: CheckResults) -> Path:
        """The report path for the current invocation."""
        if result.environment:
            python = result.environment.pretty_python_version
        else:
            python = "system"

        report_folder = self._pyproject.project_path / ".ci"
        if not report_folder.exists():
            report_folder.mkdir()

        return report_folder / ".".join(
            (
                "ci",
                python,
                self.name,
                self._pyproject.poetry.package.pretty_name,
                "xml",
            )
        )

    def _output_generic_report(self) -> None:
        """Output the test results in a standard format."""
        test_case = self.result.create_test_case(
            self.name, f"ci.{self._pyproject.poetry.package.pretty_name}"
        )
        generate_report(
            self._pyproject.poetry.package.pretty_name, self.report_path(self.result), [test_case]
        )

    def __str__(self) -> str:
        return self.name
