from itertools import cycle
from typing import (
    Any,
    Dict,
    Generator,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from coveo_functools.casing import flexfactory
from coveo_styles.styles import ExitWithFailure, echo

from coveo_stew.ci.any_runner import AnyRunner
from coveo_stew.ci.black_runner import BlackRunner
from coveo_stew.ci.mypy_runner import MypyRunner
from coveo_stew.ci.poetry_runners import PoetryCheckRunner
from coveo_stew.ci.pytest_runner import PytestRunner
from coveo_stew.ci.runner import CIPlan, ContinuousIntegrationRunner, RunnerStatus
from coveo_stew.ci.stew_runners import CheckOutdatedRunner, OfflineInstallRunner
from coveo_stew.exceptions import CannotLoadProject
from coveo_stew.stew import PythonProject

T = TypeVar("T")

CIConfig = Optional[Union[Dict[str, Any], bool]]


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

    def _generate_ci_plans(
        self, checks: Optional[List[str]], skips: Optional[List[str]], parallel: bool = True
    ) -> Generator[CIPlan, None, None]:
        """Generates one test plan per environment."""
        checks = [check.lower() for check in checks] if checks else []
        skips = [skip.lower() for skip in skips] if skips else []

        emojis = cycle(("see_no_evil", "hear_no_evil", "speak_no_evil"))

        for environment in self._pyproject.virtual_environments(create_default_if_missing=True):
            runners = []
            for runner in self.runners:
                if (checks and runner.name.lower() not in checks) or runner.name.lower() in skips:
                    echo.noise(f"{runner.name} will be skipped.", emoji=next(emojis))
                    continue
                runners.append(runner)

            yield CIPlan(environment, runners, parallel)

    async def launch_continuous_integration(
        self,
        auto_fix: bool,
        checks: Optional[List[str]],
        skips: Optional[List[str]],
        quick: bool,
        parallel: bool,
    ) -> bool:
        if self.disabled:
            return True

        ci_plans = list(self._generate_ci_plans(checks=checks, skips=skips, parallel=parallel))
        for plan in ci_plans:
            if not quick:
                self._pyproject.install(environment=plan.environment, remove_untracked=True)
            await plan.orchestrate(auto_fix)

        allowed_statuses: Tuple[RunnerStatus, ...] = (
            (RunnerStatus.Success, RunnerStatus.NotRan) if checks else (RunnerStatus.Success,)
        )

        return all(check.status in allowed_statuses for plan in ci_plans for check in plan.checks)
