import atexit
import re
from contextlib import ExitStack
from pathlib import Path
from typing import Any, Generator, Optional, Union

import importlib_resources
from cleo.io.io import IO
from cleo.io.outputs.output import Verbosity
from coveo_styles.styles import ExitWithFailure, echo
from coveo_systools.subprocess import async_check_output

from coveo_stew.ci.runner import ContinuousIntegrationRunner
from coveo_stew.ci.runner_status import RunnerStatus
from coveo_stew.environment import PythonEnvironment, PythonTool
from coveo_stew.metadata.python_api import PythonFile
from coveo_stew.stew import PythonProject


class MypyRunner(ContinuousIntegrationRunner):
    name: str = "mypy"
    check_failed_exit_codes = [1]
    outputs_own_report = True

    def __init__(
        self,
        io: IO,
        *,
        set_config: Union[str, bool] = True,
        check_paths: Optional[Union[str, list[str]]] = None,
        skip_paths: Optional[Union[str, list[str]]] = None,
        _pyproject: PythonProject,
    ) -> None:
        super().__init__(io, _pyproject=_pyproject)
        if check_paths and skip_paths:
            raise ExitWithFailure(
                failures=[
                    "`check-paths` and `skip-paths` cannot be used together",
                    f"Got: {check_paths=} {skip_paths=}",
                ],
                suggestions=[
                    "Recommended: Use only `skip-paths` to instruct the automatic detection to skip specific directories.",
                    "Use only `check-paths` to disable the automatic detection, and enumerate the folders to check.",
                    "Any specified path must be relative to the `pyproject.toml` file.",
                ],
            )

        self.set_config = set_config

        project_path = self._pyproject.project_path
        self.check_paths = self._process_check_paths(check_paths, project_path)
        self.skip_paths = self._process_skip_paths(skip_paths, project_path)

    def _process_check_paths(
        self, check_paths: Optional[Union[str, list[str]]], project_path: Path
    ) -> list[Path]:
        """Process and validate check_paths."""
        check_paths = check_paths or []
        if isinstance(check_paths, str):
            check_paths = [check_paths]

        # validate
        for path in check_paths:
            self._validate_path_is_relative(path, "check-paths")
            self._validate_typed_package(project_path / path)

        return [(project_path / path) for path in check_paths]

    def _process_skip_paths(
        self, skip_paths: Optional[Union[str, list[str]]], project_path: Path
    ) -> list[Path]:
        """Process and validate skip_paths."""
        skip_paths = skip_paths or []
        if isinstance(skip_paths, str):
            skip_paths = [skip_paths]

        # validate
        for path in skip_paths:
            self._validate_path_is_relative(path, "skip-paths")

        return [(project_path / path) for path in skip_paths]

    def _validate_path_is_relative(self, path: str, param_name: str) -> None:
        """Validate that a path is relative."""
        if Path(path).is_absolute():
            raise ExitWithFailure(
                failures=f"`{param_name}` contains absolute paths.",
                suggestions="Use a path relative to the project's `pyproject.toml` file.",
            )

    def _validate_typed_package(self, path: Path) -> None:
        """Validate that a path contains a py.typed file."""
        if not (path / PythonFile.TypedPackage).exists():
            raise ExitWithFailure(
                failures=f"No py.typed file found in {path.name}",
                suggestions=(
                    "Ensure the path is relative to the `pyproject.toml` file and contains a py.typed file, "
                    "or remove it from `check-paths`."
                ),
            )

    def _mypy_config_path(self) -> Optional[Path]:
        """Returns the path to the mypy config file."""
        if not self.set_config:
            return None

        if self.set_config is True:
            stack = ExitStack()
            atexit.register(stack.close)
            config_ref = importlib_resources.files("coveo_stew") / "package_resources/mypy.ini"
            config_path = stack.enter_context(importlib_resources.as_file(config_ref))
            return Path(config_path)  # Redundant but mypy is confused

        assert isinstance(self.set_config, str)  # mypy
        return self._pyproject.project_path / self.set_config

    def _find_typed_folders(self) -> Generator[Path, None, None]:
        """
        Yield the folders of this project that should be type-checked.
        A folder is considered a typed package if it contains a `py.typed` file at its root.

        When a folder with py.typed is found, its subdirectories are skipped.
        If skip_paths is specified, paths in that list and their subdirectories are skipped.
        """
        if self.check_paths:
            # the paths were validated at initialization
            yield from self.check_paths
            return

        project_path = self._pyproject.project_path.absolute()
        self.io.write_line(
            f"🤖 Auto detecting mypy folders from {project_path}", verbosity=Verbosity.VERBOSE
        )

        # skip the files inside virtual environments; for instance, when using `in-project-venv`, we don't
        # want to check the mypy files inside the imported libraries.
        skipped_dirs: set[Path] = {
            *(
                environment.environment_path
                for environment in self._pyproject.virtual_environments()
            ),
            *self.skip_paths,
        }

        # First collect all potential paths that contain py.typed files
        all_typed_files = list(project_path.rglob(str(PythonFile.TypedPackage)))

        # Sort by path length to process parent directories before their subdirectories.
        all_typed_files.sort(key=lambda p: len(str(p)))

        for typed_file in all_typed_files:
            typed_path = typed_file.parent

            # Skip if this directory is already within a directory we've yielded
            # or if it's within a directory specified in skip_paths
            if any(typed_path.is_relative_to(skip_dir) for skip_dir in skipped_dirs):
                self.io.write_line(
                    f"➖ Skipped: {typed_file.parent} (parent already included or skipped)",
                    verbosity=Verbosity.VERBOSE,
                )
                continue

            # Mark this directory to skip all of its subdirectories
            skipped_dirs.add(typed_path)
            self.io.write_line(f"➕ Including {typed_path}", verbosity=Verbosity.VERBOSE)
            yield typed_path

    async def _launch(
        self, environment: PythonEnvironment, *extra_args: str, **kwargs: Any
    ) -> RunnerStatus:
        working_directory = self._pyproject.project_path

        # restore absolute paths into relative ones
        typed_folders = tuple(
            folder.relative_to(working_directory) for folder in self._find_typed_folders()
        )

        if not typed_folders:
            raise ExitWithFailure(
                suggestions=[
                    "Add an empty `py.typed` file in the root of each package.",
                    "Do the same thing in test folders if you want to type-check them.",
                    "Read more: https://typing.python.org/en/latest/spec/distributing.html#packaging-typed-libraries",
                ]
            ) from Exception("Cannot find a py.typed file.")

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

        await async_check_output(
            *command,
            working_directory=self._pyproject.project_path,
            verbose=self._pyproject.verbose,
            **kwargs,
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
