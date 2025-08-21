from enum import Enum, auto
from typing import Any, Iterable, List, Optional, Tuple, Union

from cleo.io.io import IO
from coveo_styles.styles import ExitWithFailure
from coveo_systools.filesystem import find_repo_root

from coveo_stew.ci.checks.lib.base_check_cli import BaseCheckCLI
from coveo_stew.ci.checks.lib.status import CheckStatus
from coveo_stew.environment import PythonEnvironment
from coveo_stew.exceptions import CannotLoadProject, UsageError
from coveo_stew.stew import PythonProject


class WorkingDirectoryKind(Enum):
    Project = auto()
    Repository = auto()

    @classmethod
    def valid_values(cls) -> Tuple[str, ...]:
        return tuple(kind.name for kind in cls)


class CLICheck(BaseCheckCLI):
    """
    The custom checks written in the `pyproject.toml` file are handled through here.
    However, we also use it for simple builtin checks, such as black and pytest.
    """

    def __init__(
        self,
        io: IO,
        *,
        name: str,
        args: Union[str, List[str]] = "",
        check_failed_exit_codes: Iterable[int] = (1,),
        create_generic_report: bool = False,
        working_directory: str = "project",
        check_args: Optional[Union[str, List[str]]] = None,
        autofix_args: Optional[Union[str, List[str]]] = None,
        executable: Optional[str] = None,
        _pyproject: PythonProject,
    ) -> None:
        if args and check_args:
            raise ExitWithFailure(
                suggestions=f"Change all `args` for `check-args` in {_pyproject.poetry.pyproject_path}"
            ) from UsageError(
                "Cannot use `args` and `check-args` together. They are equivalent, but `args` is deprecated."
            )
        if args:
            check_args = args

        self.name = name
        super().__init__(io, _pyproject=_pyproject)

        self._executable = executable
        self.check_failed_exit_codes = check_failed_exit_codes
        self.outputs_own_report = not create_generic_report
        self.check_args = [] if check_args is None else check_args

        self.autofix_args = autofix_args
        if self.autofix_args is not None:  # some tools might autofix without any arguments
            self.supports_auto_fix = True

        try:
            self.working_directory = WorkingDirectoryKind[working_directory.title()]
        except KeyError:
            raise ExitWithFailure(
                suggestions=(
                    f"Adjust {_pyproject.poetry.pyproject_path} so that [tool.stew.ci.custom-checks.{name}] has a valid `working-directory` value.",
                    "Docs: https://github.com/coveo/stew/blob/main/README.md#options",
                )
            ) from CannotLoadProject(
                f"Working directory for {self.name} should be within {WorkingDirectoryKind.valid_values()}"
            )

    async def _do_check(self, environment: PythonEnvironment, **kwargs: Any) -> CheckStatus:
        """Run the command with check arguments."""
        args = [self.check_args] if isinstance(self.check_args, str) else self.check_args
        return await self._run(environment, *args, **kwargs)

    async def _do_autofix(self, environment: PythonEnvironment, **kwargs: Any) -> CheckStatus:
        """Run the command with autofix arguments."""
        args = [self.autofix_args] if isinstance(self.autofix_args, str) else self.autofix_args
        return await self._run(environment, *args, **kwargs)

    async def _run(self, environment: PythonEnvironment, *args: Any, **kwargs: Any) -> CheckStatus:
        command = environment.build_command(self.executable, *args)

        working_directory = self._pyproject.project_path
        if self.working_directory is WorkingDirectoryKind.Repository:
            working_directory = find_repo_root(working_directory)

        output = await self._run_command(
            command, working_directory=working_directory, env=kwargs.get("env")
        )
        self.result.output.extend(output)

        return CheckStatus.Success

    @property
    def executable(self) -> str:
        return self._executable or self.name
