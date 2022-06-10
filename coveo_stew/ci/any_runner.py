from enum import Enum, auto
from typing import Iterable, List, Optional, Tuple, Union

from coveo_styles.styles import ExitWithFailure
from coveo_systools.filesystem import find_repo_root
from coveo_systools.subprocess import async_check_output

from coveo_stew.ci.runner import ContinuousIntegrationRunner, RunnerStatus
from coveo_stew.environment import PythonEnvironment
from coveo_stew.exceptions import CannotLoadProject, UsageError
from coveo_stew.stew import PythonProject


class WorkingDirectoryKind(Enum):
    Project = auto()
    Repository = auto()

    @classmethod
    def valid_values(cls) -> Tuple[str, ...]:
        return tuple(kind.name for kind in cls)


class AnyRunner(ContinuousIntegrationRunner):
    """Custom runners"""

    def __init__(
        self,
        *,
        name: str,
        args: Union[str, List[str]] = "",
        check_failed_exit_codes: Iterable[int] = (1,),
        create_generic_report: bool = False,
        working_directory: str = "project",
        check_args: Optional[Union[str, List[str]]] = None,
        autofix_args: Optional[Union[str, List[str]]] = None,
        _pyproject: PythonProject,
    ) -> None:
        if args and check_args:
            raise ExitWithFailure(
                suggestions=f"Change all `args` for `check-args` in {_pyproject.toml_path}"
            ) from UsageError(
                "Cannot use `args` and `check-args` together. They are equivalent, but `args` is deprecated."
            )
        if args:
            check_args = args

        super().__init__(_pyproject=_pyproject)
        self._name = name
        self.check_failed_exit_codes = check_failed_exit_codes
        self.outputs_own_report = not create_generic_report
        self.check_args = [] if check_args is None else check_args
        self.autofix_args = autofix_args
        if self.autofix_args is not None:
            self._auto_fix_routine = self._custom_autofix

        try:
            self.working_directory = WorkingDirectoryKind[working_directory.title()]
        except KeyError:
            raise ExitWithFailure(
                suggestions=(
                    f"Adjust {_pyproject.toml_path} so that [tool.stew.ci.custom-runners.{name}] has a valid `working-directory` value.",
                    "Docs: https://github.com/coveo/stew/blob/main/README.md#options",
                )
            ) from CannotLoadProject(
                f"Working directory for {self.name} should be within {WorkingDirectoryKind.valid_values()}"
            )

    async def _launch(self, environment: PythonEnvironment, *extra_args: str) -> RunnerStatus:
        args = [self.check_args] if isinstance(self.check_args, str) else self.check_args
        command = environment.build_command(self.name, *args)

        working_directory = self._pyproject.project_path
        if self.working_directory is WorkingDirectoryKind.Repository:
            working_directory = find_repo_root(working_directory)

        self._last_output.extend(
            (
                await async_check_output(
                    *command,
                    *extra_args,
                    working_directory=working_directory,
                    verbose=self._pyproject.verbose,
                )
            ).split("\n")
        )

        return RunnerStatus.Success

    @property
    def name(self) -> str:
        return self._name

    async def _custom_autofix(self, environment: PythonEnvironment) -> None:
        args = [self.autofix_args] if isinstance(self.autofix_args, str) else self.autofix_args
        command = environment.build_command(self.name, *args)

        working_directory = self._pyproject.project_path
        if self.working_directory is WorkingDirectoryKind.Repository:
            working_directory = find_repo_root(working_directory)

        self._last_output.extend(
            (
                await async_check_output(
                    *command,
                    working_directory=working_directory,
                    verbose=self._pyproject.verbose,
                )
            ).split("\n")
        )
