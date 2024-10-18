from typing import Any

from coveo_systools.subprocess import DetailedCalledProcessError, async_check_output

from coveo_stew.ci.runner import ContinuousIntegrationRunner
from coveo_stew.ci.runner_status import RunnerStatus
from coveo_stew.environment import PythonEnvironment, PythonTool
from coveo_stew.stew import PythonProject


class BlackRunner(ContinuousIntegrationRunner):
    name: str = "black"
    check_failed_exit_codes = [1]

    def __init__(self, *, _pyproject: PythonProject) -> None:
        super().__init__(_pyproject=_pyproject)
        self._auto_fix_routine = self.reformat_files

    async def _launch(
        self, environment: PythonEnvironment, *extra_args: str, **kwargs: Any
    ) -> RunnerStatus:
        try:
            await self._launch_internal(environment, "--check", "--quiet", *extra_args, **kwargs)
        except DetailedCalledProcessError:
            # re-run without the quiet switch so that the output appears in the console
            await self._launch_internal(environment, "--check", *extra_args, **kwargs)
        return RunnerStatus.Success

    async def reformat_files(self, environment: PythonEnvironment, **kwargs: Any) -> None:
        await self._launch_internal(environment, "--quiet", **kwargs)

    async def _launch_internal(
        self, environment: PythonEnvironment, *extra_args: str, **kwargs: Any
    ) -> None:
        # projects may opt to use coveo-stew's black version by not including black in their dependencies.
        command = environment.build_command(PythonTool.Black, ".", *extra_args)
        await async_check_output(
            *command,
            working_directory=self._pyproject.project_path,
            verbose=self._pyproject.verbose,
            **kwargs,
        )
