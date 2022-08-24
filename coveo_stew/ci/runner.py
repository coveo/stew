import asyncio
from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from functools import cached_property
from pathlib import Path
from typing import Callable, Coroutine, Iterable, List, Optional, Sequence, Tuple

from coveo_styles.styles import ExitWithFailure, echo
from coveo_systools.subprocess import DetailedCalledProcessError
from junit_xml import TestCase

from coveo_stew.ci.reporting import generate_report
from coveo_stew.environment import PythonEnvironment
from coveo_stew.exceptions import CheckError
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
    _auto_fix_routine: Optional[Callable[[PythonEnvironment], Coroutine[None, None, None]]] = None

    def __init__(self, *, _pyproject: PythonProject) -> None:
        """Implementations may add additional keyword args."""
        self._pyproject = _pyproject
        self._last_output: List[str] = []
        self._test_cases: List[TestCase] = []
        self._last_exception: Optional[DetailedCalledProcessError] = None

    @property
    def project(self) -> PythonProject:
        return self._pyproject

    async def launch(
        self, environment: PythonEnvironment = None, *extra_args: str, auto_fix: bool = False
    ) -> "ContinuousIntegrationRunner":
        """Launch the runner's checks. Will raise on unhandled exceptions.
        Returns self for convenience with asyncio gather/as_completed/etc.
        """
        self._last_output.clear()
        self._test_cases.clear()
        try:
            self.status = await self._launch(environment, *extra_args)
        except DetailedCalledProcessError as exception:
            if exception.returncode not in self.check_failed_exit_codes:
                self.status = RunnerStatus.Error
                self._last_exception = exception
                raise
            self._last_output.extend(exception.decode_output().split("\n"))
            self._last_output.extend(exception.decode_stderr().split("\n"))
            self.status = RunnerStatus.CheckFailed

        if all((auto_fix, self.supports_auto_fix, self.status == RunnerStatus.CheckFailed)):
            echo.noise("Errors founds; launching auto-fix routine.")
            assert self._auto_fix_routine is not None  # mypy
            await self._auto_fix_routine(environment)

            # it should pass now!
            await self.launch(environment, *extra_args)
            if self.status == RunnerStatus.CheckFailed:
                echo.error("The auto fix routine was launched but the check is still failing.")
            else:
                echo.success("Auto fix was a success. Good job soldier!")

        if not self.outputs_own_report:
            self._output_generic_report(environment)

        return self

    @property
    @abstractmethod
    def name(self) -> str:
        """The friendly name of this runner."""

    @property
    def supports_auto_fix(self) -> bool:
        """Does this runner support autofix?"""
        return self._auto_fix_routine is not None

    @abstractmethod
    async def _launch(self, environment: PythonEnvironment, *extra_args: str) -> RunnerStatus:
        """Launch the continuous integration check using the given environment and store the output."""

    def echo_last_failures(self) -> None:
        """Echo the failures of the last run to the user. If there was no failure, do nothing."""
        if not self._last_output:
            return
        echo.error(self.last_output())

    def last_output(self) -> str:
        return "\n".join(self._last_output)

    @property
    def last_exception(self) -> Optional[DetailedCalledProcessError]:
        return self._last_exception

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


@dataclass
class CIPlan:
    """
    The CIPlan holds all the runners for an environment
    and orchestrates the workflow of launching them.
    """

    environment: PythonEnvironment
    checks: Sequence[ContinuousIntegrationRunner]
    parallel: bool

    @cached_property
    def autofix_checks(self) -> List[ContinuousIntegrationRunner]:
        """
        Autofix checks receive a special treatment since they will potentially change line numbers,
        making reports inaccurate.
        """
        return [check for check in self.checks if check.supports_auto_fix]

    @cached_property
    def non_autofix_checks(self) -> List[ContinuousIntegrationRunner]:
        return [check for check in self.checks if check not in self.autofix_checks]

    async def orchestrate(self, auto_fix: bool = False) -> None:
        """Orchestrates this CIPlan by launching runners in the correct order."""
        runs: List[Run] = []
        echo.step(
            f"Planned {len(self.checks)} runners for {self.environment.pretty_python_version}"
        )

        if auto_fix:
            # run autofix first, in parallel
            runs.append(run := Run(self.environment, self.autofix_checks))
            await run.run_and_report(parallel=self.parallel)

            if run.overall_status is RunnerStatus.CheckFailed:
                await run.run_and_report(auto_fix=True, feedback=False, parallel=False)
                await run.run_and_report(parallel=self.parallel)  # verify that autofix worked

            # run all other runners
            runs.append(run := Run(self.environment, self.non_autofix_checks))
            await run.run_and_report(parallel=self.parallel)

        else:
            runs.append(run := Run(self.environment, self.checks))
            await run.run_and_report(parallel=self.parallel)

        overall_status = get_overall_run_status(*runs)
        echo.success(
            f"The CI run for {self.environment.pretty_python_version} completed with status: {overall_status}"
        )

        if exceptions := [exception for run in runs for exception in run.exceptions]:
            raise ExitWithFailure(
                suggestions=(
                    "If a command should be treated as a check failure, specify `check-failed-exit-codes`",
                    "Reference: https://github.com/coveo/stew/blob/main/README.md#options)",
                    "Try the commands in a shell to troubleshoot them faster.",
                ),
                failures=(
                    f"\n------- [{runner} failed unexpectedly] -------\n\n{str(ex)}\n"
                    for runner, ex in exceptions
                ),
            ) from CheckError("Unexpected errors occurred when launching external processes.")


@dataclass
class Run:
    """The Run is a stateful object that runs checks and reports the results to the user."""

    environment: PythonEnvironment
    checks: Sequence[ContinuousIntegrationRunner]

    @cached_property
    def exceptions(self) -> List[Tuple[ContinuousIntegrationRunner, DetailedCalledProcessError]]:
        """Exceptions are stored here after the run. Exceptions are cleared when `run_and_report` is called."""
        return []

    @property
    def overall_status(self) -> RunnerStatus:
        return get_overall_run_status(self)

    async def run_and_report(
        self, auto_fix: bool = False, feedback: bool = True, parallel: bool = True
    ) -> None:
        """Launch the runners and report the results to the user."""
        self.exceptions.clear()

        if auto_fix and parallel:
            raise AssertionError(
                "Some dev made a mistake; parallel and autofix are mutually exclusive!"
            )

        if parallel:
            for next_result in asyncio.as_completed(
                [runner.launch(self.environment, auto_fix=False) for runner in self.checks]
            ):
                self._report(await next_result, feedback=feedback)
        else:
            for runner in self.checks:
                self._report(
                    await runner.launch(self.environment, auto_fix=auto_fix), feedback=feedback
                )

        if self.exceptions:
            for check, exception in self.exceptions:
                echo.warning(f"The runner {check} created an exception: ", pad_before=True)
                echo.noise(exception, pad_after=True)

    def _report(self, check: ContinuousIntegrationRunner, feedback: bool = True) -> None:
        """Reports on a completed check."""
        if check.status is RunnerStatus.Error:
            self.exceptions.append((check, check.last_exception))

        if feedback:
            if check.status is RunnerStatus.Success:
                echo.normal(f"PASSED: {check}", emoji="heavy_check_mark", fg="green")
                if check.project.verbose:
                    check.echo_last_failures()

            elif check.status is RunnerStatus.CheckFailed:
                echo.warning(
                    f"{check.project.package.name}: {check} reported issues:",
                    pad_before=False,
                    pad_after=False,
                )
                check.echo_last_failures()

            elif check.status is RunnerStatus.Error:
                echo.error(
                    f"The ci runner {check} failed to complete "
                    f"due to an environment or configuration error."
                )
                check.echo_last_failures()


def get_overall_run_status(*runs: Run) -> RunnerStatus:
    """Return the overall run status for the provided runs."""
    statuses = [check.status for run in runs for check in run.checks]
    for status in RunnerStatus.Error, RunnerStatus.CheckFailed, RunnerStatus.Success:
        if status in statuses:
            return status

    return RunnerStatus.NotRan
