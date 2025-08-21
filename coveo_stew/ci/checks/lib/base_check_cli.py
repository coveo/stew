import os
from abc import ABCMeta
from pathlib import Path
from typing import Dict, Iterable, Optional

from cleo.io.io import IO
from coveo_systools.subprocess import DetailedCalledProcessError, async_check_output

from coveo_stew.ci.checks.lib.base_check import BaseCheck, CheckFunction
from coveo_stew.ci.checks.lib.status import CheckStatus
from coveo_stew.ci.reporting.reporting import (
    format_detailed_called_process_error_output,
)
from coveo_stew.environment import PythonEnvironment
from coveo_stew.stew import PythonProject


class BaseCheckCLI(BaseCheck, metaclass=ABCMeta):
    """Base class for checks that execute commands via CLI."""

    # exit codes that indicate a failed check rather than an error
    check_failed_exit_codes: Iterable[int] = []

    def __init__(self, io: IO, *, _pyproject: PythonProject) -> None:
        super().__init__(io, _pyproject=_pyproject)

    async def _execute_check_function(
        self,
        fn: CheckFunction,
        environment: PythonEnvironment,
    ) -> CheckStatus:
        """Execute the CheckFunction with CLI-specific wrapping."""
        environment_variables = os.environ.copy()
        # try to set the terminal width if available
        if os.isatty(0):
            try:
                environment_variables["COLUMNS"] = str(os.get_terminal_size().columns)
            except OSError:
                pass

        try:
            return await fn(environment, env=environment_variables)
        except DetailedCalledProcessError as exception:
            if exception.returncode not in self.check_failed_exit_codes:
                raise

            self.result.output.append("")
            self.result.output.extend(
                format_detailed_called_process_error_output(
                    exception,
                    # Include verbose output if the IO is set to verbose
                    is_error_or_verbose=self.io.is_verbose(),
                )
            )
            return CheckStatus.CheckFailed

    async def _run_command(
        self,
        command: list[str],
        *,
        working_directory: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> list[str]:
        """Run a command and return its output lines.

        Any failure to run the command will raise a DetailedCalledProcessError.
        """
        output = await async_check_output(
            *command,
            working_directory=working_directory or self._pyproject.project_path,
            verbose=self._pyproject.verbose,
            remove_ansi=False,
            env=env,
        )
        return output.splitlines()
