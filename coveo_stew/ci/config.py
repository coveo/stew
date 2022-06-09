import asyncio
from asyncio import Future
from collections.abc import Coroutine
from dataclasses import dataclass, field
from functools import partial
from typing import (
    Any,
    Dict,
    Iterator,
    Optional,
    Type,
    TypeVar,
    Union,
    List,
    Iterable,
    Tuple,
    Callable,
    Sequence,
    Generator,
)

from coveo_functools.casing import flexfactory
from coveo_styles.styles import ExitWithFailure, echo
from coveo_systools.subprocess import DetailedCalledProcessError

from coveo_stew.ci.any_runner import AnyRunner
from coveo_stew.ci.black_runner import BlackRunner
from coveo_stew.ci.mypy_runner import MypyRunner
from coveo_stew.ci.poetry_runners import PoetryCheckRunner
from coveo_stew.ci.pytest_runner import PytestRunner
from coveo_stew.ci.runner import ContinuousIntegrationRunner, RunnerStatus
from coveo_stew.ci.stew_runners import CheckOutdatedRunner, OfflineInstallRunner
from coveo_stew.environment import PythonEnvironment
from coveo_stew.exceptions import CannotLoadProject, CheckError
from coveo_stew.stew import PythonProject

T = TypeVar("T")

CIConfig = Optional[Union[Dict[str, Any], bool]]
CheckExecutor = Coroutine[Any, Any, RunnerStatus]


@dataclass
class CIPlan:
    environment: PythonEnvironment
    sequential_checks: List[ContinuousIntegrationRunner] = field(default_factory=list)
    parallel: List[ContinuousIntegrationRunner] = field(default_factory=list)


class ContinuousIntegrationConfig:
    def __init__(
        self,
        *,
        disabled: bool = False,
        mypy: CIConfig = True,
        check_outdated: CIConfig = True,
        poetry_check: CIConfig = True,
        pytest: CIConfig = False,
        offline_build: CIConfig = False,
        black: CIConfig = False,
        custom_runners: Optional[Dict[str, CIConfig]] = None,
        _pyproject: PythonProject,
    ):
        self._pyproject = _pyproject
        self.disabled = disabled  # a master switch used by stew to skip this project.

        self._runners: Dict[str, Optional[ContinuousIntegrationRunner]] = {
            "check-outdated": self._flexfactory(CheckOutdatedRunner, check_outdated),
            "offline-build": self._flexfactory(OfflineInstallRunner, offline_build),
            "mypy": self._flexfactory(MypyRunner, mypy),
            "pytest": self._flexfactory(PytestRunner, pytest),
            "poetry-check": self._flexfactory(PoetryCheckRunner, poetry_check),
            "black": self._flexfactory(BlackRunner, black),
        }

        # these builtin runners are specialized and cannot be overwritten.
        if custom_runners and (
            culprits := {"check-outdated", "offline-build"}.intersection(custom_runners)
        ):
            raise ExitWithFailure(
                suggestions=(
                    f"You can configure {culprits} using the [tool.stew.ci] section.",
                    "Docs: https://github.com/coveo/stew/blob/main/README.md#options",
                )
            ) from CannotLoadProject(
                "Cannot define `check-outdated` and `offline-build` as custom runners."
            )

        # everything else can be redefined as a custom runner
        for runner_name, runner_config in (custom_runners or {}).items():
            self._runners[runner_name] = self._flexfactory(
                AnyRunner, runner_config, name=runner_name
            )

    def _flexfactory(self, cls: Type[T], config: Optional[CIConfig], **extra: str) -> Optional[T]:
        """handles the true form of the config. like mypy = true"""
        if config in (None, False):
            return None
        if config is True:
            config = {}
        return flexfactory(cls, **config, **extra, _pyproject=self._pyproject)  # type: ignore

    @property
    def runners(self) -> Iterator[ContinuousIntegrationRunner]:
        """Iterate the configured runners for this project."""
        yield from sorted(
            filter(bool, self._runners.values()),
            # autofix-enabled runners must run first because they may change the code.
            # if e.g. mypy finds errors and then black fixes the file, the line numbers from mypy may no longer
            # be valid.
            key=lambda runner: 0 if runner.supports_auto_fix else 1,
        )

    def get_runner(self, runner_name: str) -> Optional[ContinuousIntegrationRunner]:
        """Obtain a runner by name."""
        return self._runners.get(runner_name)

    def _generate_test_plan(
        self, checks: Optional[List[str]], parallel: bool
    ) -> Generator[CIPlan, None, None]:
        """Generates one test plan per environment."""
        for environment in self._pyproject.virtual_environments(create_default_if_missing=True):
            future = CIPlan(environment)

            for runner in self.runners:
                if checks and runner.name.lower() not in checks:
                    continue

                workflow = (
                    future.sequential_checks
                    if (runner.supports_auto_fix or not parallel)
                    else future.parallel
                )
                workflow.append(runner)

            yield future

    async def launch_continuous_integration(
        self, auto_fix, checks: Optional[List[str]], quick: bool, parallel: bool
    ) -> bool:
        if self.disabled:
            return True

        checks = [check.lower() for check in checks or []]
        exceptions: List[Tuple[ContinuousIntegrationRunner, DetailedCalledProcessError]] = []

        test_plans = list(self._generate_test_plan(checks=checks, parallel=parallel))

        for plan in test_plans:
            if not quick:
                self._pyproject.install(environment=plan.environment, remove_untracked=True)

            for sequential_check in plan.sequential_checks:
                echo.step("Launching sequential checks...")
                await asyncio.gather(
                    sequential_check.launch(plan.environment, auto_fix=auto_fix),
                    return_exceptions=True,
                )
                echo.step("Launching parallel checks...")
            await asyncio.gather(
                *(parallel_check.launch(plan.environment) for parallel_check in plan.parallel),
                return_exceptions=True,
            )

        for plan in test_plans:
            for check in plan.sequential_checks:
                echo.normal(
                    f"{check} ({plan.environment.pretty_python_version})", emoji="hourglass"
                )

                if check.status is RunnerStatus.Error:
                    echo.error(
                        f"The ci runner {check} failed to complete "
                        f"due to an environment or configuration error."
                    )
                    exceptions.append((check, check.last_exception))

                if check.status is not RunnerStatus.Success:
                    echo.warning(
                        f"{self._pyproject.package.name}: {check} reported issues:",
                        pad_before=False,
                        pad_after=False,
                    )
                    check.echo_last_failures()

        if exceptions:
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

        allowed_statuses: Tuple[RunnerStatus, ...] = (
            (RunnerStatus.Success, RunnerStatus.NotRan) if checks else (RunnerStatus.Success,)
        )
        return all(runner.status in allowed_statuses for runner in self.runners)
