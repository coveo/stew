from typing import TypeVar, Any, Dict, Optional, Iterator, Union, Type

from coveo_functools.casing import flexfactory
from coveo_stew.ci.any_runner import AnyRunner

from coveo_stew.ci.black_runner import BlackRunner
from coveo_stew.ci.mypy_runner import MypyRunner
from coveo_stew.ci.poetry_runners import PoetryCheckRunner
from coveo_stew.ci.stew_runners import CheckOutdatedRunner, OfflineInstallRunner
from coveo_stew.ci.pytest_runner import PytestRunner
from coveo_stew.ci.runner import ContinuousIntegrationRunner
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
        if custom_runners and {"check-outdated", "offline-build"}.intersection(custom_runners):
            raise CannotLoadProject(
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
