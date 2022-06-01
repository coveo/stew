from pathlib import Path
from subprocess import PIPE

import pkg_resources
import re
from typing import Generator, Union, Optional

from coveo_styles.styles import echo
from coveo_systools.subprocess import check_output

from coveo_stew.ci.runner import ContinuousIntegrationRunner, RunnerStatus
from coveo_stew.environment import PythonEnvironment, PythonTool
from coveo_stew.metadata.python_api import PythonFile
from coveo_stew.stew import PythonProject


class MypyRunner(ContinuousIntegrationRunner):
    name: str = "mypy"
    check_failed_exit_codes = [1]
    outputs_own_report = True

    def __init__(self, *, set_config: Union[str, bool] = True, _pyproject: PythonProject) -> None:
        super().__init__(_pyproject=_pyproject)
        self.set_config = set_config

    def _mypy_config_path(self) -> Optional[Path]:
        """Returns the path to the mypy config file."""
        if not self.set_config:
            return None

        if self.set_config is True:
            return Path(pkg_resources.resource_filename("coveo_stew", "package_resources/mypy.ini"))

        assert isinstance(self.set_config, str)  # mypy
        return self._pyproject.project_path / self.set_config

    def _find_typed_folders(self) -> Generator[Path, None, None]:
        """Yield the folders of this project that should be type-checked."""
        yield from filter(
            lambda path: (path / PythonFile.TypedPackage).exists(),
            self._pyproject.project_path.iterdir(),
        )

    def _launch(self, environment: PythonEnvironment, *extra_args: str) -> RunnerStatus:
        typed_folders = tuple(folder.name for folder in self._find_typed_folders())

        if not typed_folders:
            self._last_output = [
                "Cannot find a py.typed file: https://www.python.org/dev/peps/pep-0561/"
            ]
            return RunnerStatus.Error

        args = [
            # the --python-executable switch tells mypy in which environment the imports should be followed.
            "--python-executable",
            environment.python_executable,
            "--cache-dir",
            self._pyproject.project_path / ".mypy_cache",
            "--show-error-codes",
            f"--junit-xml={self.report_path(environment)}",
        ]

        mypy_config = self._mypy_config_path()
        if mypy_config:
            args.append("--config-file")
            args.append(mypy_config)

        command = environment.build_command(
            PythonTool.Mypy,
            *args,
            *extra_args,  # any extra argument provided by the caller
            *typed_folders,  # what to lint
        )

        if self._pyproject.verbose:
            echo.normal(command)

        check_output(
            *command,
            working_directory=self._pyproject.project_path,
            verbose=self._pyproject.verbose,
            stderr=PIPE,
        )
        return RunnerStatus.Success

    def echo_last_failures(self) -> None:
        if not self._last_output:
            return

        pattern = re.compile(
            r"^(?P<path>.+\.py):(?P<line>\d+):(?P<column>\d+(?::)| )"
            r"(?:\s?error:\s?)(?P<detail>.+)$"
        )

        for line in self._last_output:
            match = pattern.fullmatch(line)
            if match:
                adjusted_path = (self._pyproject.project_path / Path(match["path"])).resolve()
                echo.error_details(
                    f'{adjusted_path}:{match["line"]}:{match["column"]} {match["detail"]}'
                )
            else:
                echo.noise(line)
