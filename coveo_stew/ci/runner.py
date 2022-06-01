from abc import abstractmethod
from enum import Enum, auto
from pathlib import Path
from typing import List, Optional, Callable, Iterable

from coveo_systools.subprocess import DetailedCalledProcessError
from coveo_styles.styles import echo
from junit_xml import TestCase

from coveo_stew.ci.reporting import generate_report
from coveo_stew.environment import PythonEnvironment
from coveo_stew.stew import PythonProject


class RunnerStatus(Enum):
    NotRan = auto()
    Success = auto()
    CheckFailed = auto()
    Error = auto()

    def __str__(self) -> str:
        return self.name


class ContinuousIntegrationRunner:
    status: RunnerStatus = RunnerStatus.NotRan
    check_failed_exit_codes: Iterable[int] = []
    outputs_own_report: bool = False  # set to True if the runner produces its own report.

    # implementations may provide an auto fix routine.
    _auto_fix_routine: Optional[Callable[[PythonEnvironment], None]] = None

    def __init__(self, *, _pyproject: PythonProject) -> None:
        """Implementations may add additional keyword args."""
        self._pyproject = _pyproject
        self._last_output: List[str] = []
        self._test_cases: List[TestCase] = []

    def launch(
        self, environment: PythonEnvironment = None, *extra_args: str, auto_fix: bool = False
    ) -> RunnerStatus:
        """Launch the runner's checks. Will raise on unhandled exceptions."""
        self._last_output.clear()
        self._test_cases.clear()
        try:
            self.status = self._launch(environment, *extra_args)
        except DetailedCalledProcessError as exception:
            if exception.returncode not in self.check_failed_exit_codes:
                self.status = RunnerStatus.Error
                raise
            self._last_output.extend(exception.decode_output().split("\n"))
            self._last_output.extend(exception.decode_stderr().split("\n"))
            self.status = RunnerStatus.CheckFailed

        if all((auto_fix, self.supports_auto_fix, self.status == RunnerStatus.CheckFailed)):
            echo.noise("Errors founds; launching auto-fix routine.")
            self._auto_fix_routine(environment)

            # it should pass now!
            self.launch(environment, *extra_args)
            if self.status == RunnerStatus.CheckFailed:
                echo.error("The auto fix routine was launched but the check is still failing.")
            else:
                echo.success("Auto fix was a success. Good job soldier!")

        if not self.outputs_own_report:
            self._output_generic_report(environment)

        return self.status

    @property
    @abstractmethod
    def name(self) -> str:
        """The friendly name of this runner."""

    @property
    def supports_auto_fix(self) -> bool:
        """Does this runner support autofix?"""
        return self._auto_fix_routine is not None

    @abstractmethod
    def _launch(self, environment: PythonEnvironment, *extra_args: str) -> RunnerStatus:
        """Launch the continuous integration check using the given environment and store the output."""

    def echo_last_failures(self) -> None:
        """Echo the failures of the last run to the user. If there was no failure, do nothing."""
        if not self._last_output:
            return
        echo.error(self.last_output())

    def last_output(self) -> str:
        return "\n".join(self._last_output)

    def report_path(self, environment: PythonEnvironment) -> Path:
        """The report path for the current invocation. e.g.: ci.py3.6.2.mypy.coveo-functools.xml"""
        report_folder = self._pyproject.project_path / ".ci"
        if not report_folder.exists():
            report_folder.mkdir()

        return report_folder / ".".join(
            (
                "ci",
                environment.pretty_python_version,
                self.name,
                self._pyproject.package.name,
                "xml",
            )
        )

    def _output_generic_report(self, environment: PythonEnvironment) -> None:
        test_case = TestCase(self.name, classname=f"ci.{self._pyproject.package.name}")
        if self.status is RunnerStatus.Error:
            test_case.add_error_info(
                "An error occurred, the test was unable to complete.", self.last_output()
            )
        elif self.status is RunnerStatus.CheckFailed:
            test_case.add_failure_info("The test completed; errors were found.", self.last_output())
        generate_report(self._pyproject.package.name, self.report_path(environment), [test_case])

    def __str__(self) -> str:
        return self.name
