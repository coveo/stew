from typing import (
    Any,
    Dict,
    Iterator,
    Optional,
    Type,
    Union,
)

from cleo.io.io import IO
from coveo_functools.casing import flexfactory
from coveo_styles.styles import ExitWithFailure

from coveo_stew.ci.checks.black import CheckBlack
from coveo_stew.ci.checks.lib.base_check import BaseCheck
from coveo_stew.ci.checks.lib.cli_check import CLICheck
from coveo_stew.ci.checks.mypy import CheckMypy
from coveo_stew.ci.checks.poetry import CheckPoetry
from coveo_stew.ci.checks.pytest import CheckPytest
from coveo_stew.ci.checks.stew import CheckOfflineBuild, CheckOutdated
from coveo_stew.ci.orchestration.orchestrator import T
from coveo_stew.exceptions import CannotLoadProject
from coveo_stew.stew import PythonProject

CheckConfig = Optional[Union[dict[str, Any], bool]]


class StewCIConfig:
    def __init__(
        self,
        io: IO,
        *,
        disabled: bool = False,
        mypy: CheckConfig = True,
        check_outdated: CheckConfig = True,
        poetry_check: CheckConfig = True,
        pytest: CheckConfig = False,
        offline_build: CheckConfig = False,
        black: CheckConfig = False,
        # don't rename custom_runners, it directly matches the `stew.ci.custom-runners` key in pyproject.toml!
        custom_runners: Optional[dict[str, CheckConfig]] = None,
        _pyproject: PythonProject,
    ):
        self._io = io
        self._pyproject = _pyproject
        self.disabled = disabled  # a master switch used by stew to skip this project.

        self._checks: Dict[str, Optional[BaseCheck]] = {
            "check-outdated": self._flexfactory(CheckOutdated, check_outdated),
            "offline-build": self._flexfactory(CheckOfflineBuild, offline_build),
            "mypy": self._flexfactory(CheckMypy, mypy),
            "pytest": self._flexfactory(CheckPytest, pytest),
            "poetry-check": self._flexfactory(CheckPoetry, poetry_check),
            "black": self._flexfactory(CheckBlack, black),
        }

        # these builtin checks are specialized and cannot be overwritten.
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

        # everything else can be redefined as a custom check
        for check_name, check_config in (custom_runners or {}).items():
            self._checks[check_name] = self._flexfactory(CLICheck, check_config, name=check_name)

    def _flexfactory(
        self, cls: Type[T], config: Optional[CheckConfig], **extra: str
    ) -> Optional[T]:
        """handles the true form of the config. like mypy = true"""
        if config in (None, False):
            return None
        if config is True:
            config = {}
        return flexfactory(cls, **config, **extra, _pyproject=self._pyproject, io=self._io)  # type: ignore

    @property
    def checks(self) -> Iterator[BaseCheck]:
        """Iterate the configured checks for this project."""
        yield from sorted(
            filter(bool, self._checks.values()),
            # autofix-enabled checks must run first because they may change the code.
            # if e.g. mypy finds errors and then black fixes the file, the line numbers from mypy may no longer
            # be valid.
            key=lambda check: 0 if check.supports_auto_fix else 1,
        )

    def get_check(self, check_name: str) -> Optional[BaseCheck]:
        """Obtain a check by name."""
        return self._checks.get(check_name)
