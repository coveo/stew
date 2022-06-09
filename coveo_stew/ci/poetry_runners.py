from coveo_stew.ci.runner import ContinuousIntegrationRunner, RunnerStatus
from coveo_stew.environment import PythonEnvironment, PythonTool
from coveo_systools.subprocess import check_output, async_check_output


class PoetryCheckRunner(ContinuousIntegrationRunner):
    name: str = "poetry-check"
    check_failed_exit_codes = [1]

    async def _launch(self, environment: PythonEnvironment, *extra_args: str) -> RunnerStatus:
        await async_check_output(
            *environment.build_command(PythonTool.Poetry, "check"),
            working_directory=self._pyproject.project_path
        )
        return RunnerStatus.Success
