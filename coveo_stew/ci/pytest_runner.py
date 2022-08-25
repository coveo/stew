from coveo_systools.subprocess import async_check_output

from coveo_stew.ci.runner import ContinuousIntegrationRunner
from coveo_stew.ci.runner_status import RunnerStatus
from coveo_stew.environment import PythonEnvironment, PythonTool
from coveo_stew.stew import PythonProject


class PytestRunner(ContinuousIntegrationRunner):
    name: str = "pytest"
    check_failed_exit_codes = [1]
    outputs_own_report = True

    def __init__(
        self,
        *,
        marker_expression: str = None,
        doctest_modules: bool = True,
        _pyproject: PythonProject,
    ) -> None:
        super().__init__(_pyproject=_pyproject)
        self.marker_expression = marker_expression
        self.doctest_modules: bool = doctest_modules

    async def _launch(self, environment: PythonEnvironment, *extra_args: str) -> RunnerStatus:
        command = environment.build_command(
            PythonTool.Pytest,
            "--durations=5",
            "--tb=short",
            f"--junitxml={self.report_path(environment)}",
        )

        if self.marker_expression:
            command.extend(("-m", self.marker_expression))
        if self.doctest_modules:
            command.append("--doctest-modules")

        await async_check_output(
            *command,
            *extra_args,
            working_directory=self._pyproject.project_path,
            verbose=self._pyproject.verbose,
        )

        return RunnerStatus.Success
