"""Interact with python projects programmatically."""

from contextlib import contextmanager
import os
from pathlib import Path
import re
import shutil
from shutil import rmtree
import sys
from typing import Generator, Optional, Any, List, Tuple, Iterator, Dict
import warnings

from coveo_functools.casing import flexfactory
from coveo_itertools.lookups import dict_lookup
from coveo_styles.styles import echo
from coveo_systools.filesystem import find_repo_root, CannotFindRepoRoot
from coveo_systools.subprocess import check_run, DetailedCalledProcessError

from coveo_stew.environment import PythonEnvironment, PythonTool, find_python_tool
from coveo_stew.exceptions import PythonProjectException, NotAPoetryProject
from coveo_stew.metadata.stew_api import StewPackage
from coveo_stew.metadata.poetry_api import PoetryAPI
from coveo_stew.metadata.python_api import PythonFile

from coveo_stew.utils import load_toml_from_path


class PythonProject:
    """Access the information within a pyproject.toml file and operate on them."""

    def __init__(self, project_path: Path, *, verbose: bool = False) -> None:
        self.verbose = verbose
        self.project_path: Path = (
            project_path if project_path.is_dir() else project_path.parent
        ).absolute()
        self.toml_path: Path = self.project_path / PythonFile.PyProjectToml
        self.lock_path: Path = self.project_path / PythonFile.PoetryLock

        toml_content = load_toml_from_path(self.toml_path)

        try:
            self.package: PoetryAPI = flexfactory(
                PoetryAPI, **dict_lookup(toml_content, "tool", "poetry")
            )
        except KeyError as exception:
            raise NotAPoetryProject from exception

        self.egg_path: Path = self.project_path / f"{self.package.safe_name}.egg-info"

        self.options: StewPackage = flexfactory(
            StewPackage,
            **dict_lookup(toml_content, "tool", "stew", default={}),
            _pyproject=self,
        )

        from coveo_stew.ci.config import ContinuousIntegrationConfig  # circular import

        if self.options.pydev:
            # ensure no steps are repeated. pydev projects only receive basic poetry/lock checks
            self.ci: ContinuousIntegrationConfig = ContinuousIntegrationConfig(
                check_outdated=True, poetry_check=True, mypy=False, _pyproject=self
            )
        else:
            self.ci = flexfactory(
                ContinuousIntegrationConfig,
                **dict_lookup(toml_content, "tool", "stew", "ci", default={}),
                _pyproject=self,
            )

        try:
            repo_root: Optional[Path] = find_repo_root(self.project_path)
        except CannotFindRepoRoot:
            repo_root = None

        self.repo_root: Optional[Path] = repo_root
        self._cached_environments: Optional[Dict[Path, PythonEnvironment]] = None

    def relative_path(self, path: Path) -> Path:
        """returns the relative path of a path vs the project folder."""
        return path.relative_to(self.project_path)

    @classmethod
    def find_pyproject(
        cls, project_name: str, path: Path = None, *, verbose: bool = False
    ) -> "PythonProject":
        warnings.warn(
            "This functionality moved to the `coveo_stew.discovery` module.", DeprecationWarning
        )
        from coveo_stew.discovery import find_pyproject

        return find_pyproject(project_name, path, verbose=verbose)

    @classmethod
    def find_pyprojects(
        cls,
        path: Path = None,
        *,
        query: str = None,
        exact_match: bool = False,
        verbose: bool = False,
    ) -> Generator["PythonProject", None, None]:
        """Factory; scan a path (recursive) and return a PythonProject instance for each pyproject.toml

        Parameters:
            path: where to start looking for pyproject.toml files.
            query: substring for package selection. '-' and '_' are equivalent.
            exact_match: turns query into an exact match (except for - and _). Recommended use: CI scripts
            verbose: output more details to command line
        """
        warnings.warn(
            "This functionality moved to the `coveo_stew.discovery` module.", DeprecationWarning
        )
        from coveo_stew.discovery import discover_pyprojects

        yield from discover_pyprojects(path, query=query, exact_match=exact_match, verbose=verbose)

    @property
    def lock_is_outdated(self) -> bool:
        """True if the toml file has pending changes that were not applied to poetry.lock"""
        if not self.lock_path.exists():
            return False

        # yolo: use the dry run output to determine if the lock is too old
        dry_run_output = self.poetry_run(
            "install", "--remove-untracked", "--dry-run", capture_output=True
        )

        for sentence in (
            "Warning: The lock file is not up to date",
            "outdated dependencies",
            "Run update to update them",
        ):
            if sentence.casefold() in dry_run_output.casefold():
                return True

        return False

    @property
    def activated_environment(self) -> Optional[PythonEnvironment]:
        """The environment activated for a project.

        Note: cached for performance, could theoretically become out-of-sync with reality, either due to a bug,
        or because someone called `poetry env use` while we were working :shrug:

        To prevent out of sync:
            - Use the context manager `self._activate_poetry_environment`
            - or use the `environment` argument of `self.poetry_run`
        """
        return next(
            (environment for environment in self.virtual_environments() if environment.activated),
            None,
        )

    def virtual_environments(
        self, *, create_default_if_missing: bool = False
    ) -> Iterator[PythonEnvironment]:
        """The project's virtual environments. These are cached for performance.

        create_default_if_missing: When no environments are found, install the environment using what poetry
            would use by default.
        """
        reevaluate = self._cached_environments is None or all(
            (
                # we already have a cache
                self._cached_environments is not None,
                # but it's empty
                not self._cached_environments,
                # and we are supposed to create one
                create_default_if_missing,
            )
        )

        if reevaluate:
            self._refresh_virtual_environment_cache()
            if not self._cached_environments and create_default_if_missing:
                self.install()
                self._refresh_virtual_environment_cache()

        yield from self._cached_environments.values()

    def _refresh_virtual_environment_cache(self) -> None:
        if self._cached_environments is None:
            self._cached_environments = {}

        for path in self._get_virtual_environment_paths():
            if path not in self._cached_environments:
                self._cached_environments[path] = PythonEnvironment(path)

        # reprocess all environments to set the activated_environment one correctly
        try:
            activated_environment: Optional[PythonEnvironment] = PythonEnvironment(
                self.poetry_run("env", "info", "--path", capture_output=True, breakout_of_venv=True)
            )
        except DetailedCalledProcessError as exception:
            if exception.returncode != 1:
                raise
            activated_environment = None

        for environment in self._cached_environments.values():
            environment.activated = (
                (environment == activated_environment) if activated_environment else False
            )

    def _get_virtual_environment_paths(self) -> Iterator[Path]:
        for str_path in self.poetry_run(
            "env", "list", "--full-path", capture_output=True, breakout_of_venv=True
        ).split("\n"):
            if str_path.strip():
                yield Path(str_path.replace("(Activated)", "").strip())

    def current_environment_belongs_to_project(self) -> bool:
        """True if we're running from one of the project's virtual envs.
        Typically False; serves the rare cases where stew is installed inside the environment.
        """
        current_executable = Path(sys.executable)
        return any(
            environment.python_executable == current_executable
            for environment in self.virtual_environments()
        )

    def bump(self) -> bool:
        """Bump (update) all dependencies to the lock file. Return True if changed."""
        if not self.lock_path.exists():
            return self.lock_if_needed()

        content = self.lock_path.read_text()
        self.poetry_run("update", "--lock", breakout_of_venv=True)
        if content != self.lock_path.read_text():
            return True
        return False

    def build(self, target_path: Path = None) -> Path:
        """Builds the package's wheel. If a path is provided, it will be moved there.
        Returns final path to the artifact."""
        # like coredump_detector-0.0.1-py3-none-any.whl
        wheel_pattern = re.compile(r"(?P<distribution>\S+?)-(?P<version>.+?)-(?P<extra>.+)\.whl")
        poetry_output = self.poetry_run("build", "--format", "wheel", capture_output=True)
        wheel_match = wheel_pattern.search(poetry_output)

        if not wheel_match:
            raise PythonProjectException(
                f"Unable able to find a wheel filename in poetry's output:\n{poetry_output}"
            )

        assert wheel_match["distribution"] == self.package.safe_name
        assert wheel_match["version"] == str(self.package.version)
        wheel = (
            self.project_path / "dist" / Path(wheel_match.group())
        )  # group() gives the complete match
        assert wheel.exists(), f"{wheel} cannot be found."

        if target_path is None:
            # no move necessary; we're done
            return wheel

        target = target_path / wheel.name
        if not target_path.exists():
            target_path.mkdir(parents=True)
        assert target_path.is_dir()
        shutil.move(str(wheel), str(target))

        return target

    def export(self) -> str:
        """Generates the content of a `requirements.txt` file based on the lock."""
        return self.poetry_run("export", capture_output=True)

    def launch_continuous_integration(
        self, auto_fix: bool = False, checks: List[str] = None, quick: bool = False
    ) -> bool:
        """Launch all continuous integration runners on the project."""
        from coveo_stew.ci.runner import RunnerStatus  # circular import

        if self.ci.disabled:
            return True

        checks = [check.lower() for check in checks or []]
        exceptions: List[DetailedCalledProcessError] = []
        for environment in self.virtual_environments(create_default_if_missing=True):
            if not quick:
                self.install(environment=environment, remove_untracked=True)
            for runner in self.ci.runners:
                if checks and runner.name.lower() not in checks:
                    continue

                try:
                    echo.normal(
                        f"{runner} ({environment.pretty_python_version})", emoji="hourglass"
                    )
                    status = runner.launch(environment, auto_fix=auto_fix)
                    if status is not RunnerStatus.Success:
                        echo.warning(
                            f"{self.package.name}: {runner} reported issues:",
                            pad_before=False,
                            pad_after=False,
                        )
                        runner.echo_last_failures()

                except DetailedCalledProcessError as exception:
                    echo.error(
                        f"The ci runner {runner} failed to complete "
                        f"due to an environment or configuration error."
                    )
                    exceptions.append(exception)

        if exceptions:
            if len(exceptions) > 1:
                echo.warning(f"{len(exceptions)} exceptions found; raising first one.")
            raise exceptions[0]

        allowed_statuses: Tuple[RunnerStatus, ...] = (
            (RunnerStatus.Success, RunnerStatus.NotRan) if checks else (RunnerStatus.Success,)
        )
        return all(runner.status in allowed_statuses for runner in self.ci.runners)

    def install(
        self,
        *,
        environment: PythonEnvironment = None,
        remove_untracked: bool = False,
        quiet: bool = False,
    ) -> None:
        """
        Performs a 'poetry install --remove-untracked' on the project. If an environment is provided, target it.
        """
        target_environment = environment or self.activated_environment
        if target_environment and target_environment.installed:
            # this environment was already installed
            if not (remove_untracked and not target_environment.cleaned):
                # return unless we are cleaning a non-cleaned environment
                return

        command = ["install"]
        if remove_untracked:
            command.append("--remove-untracked")
        if quiet and not self.verbose:
            command.append("--quiet")

        self.poetry_run(*command, environment=target_environment)

        self._refresh_virtual_environment_cache()
        affected_environment = target_environment or self.activated_environment
        affected_environment.installed = True
        affected_environment.cleaned |= remove_untracked

    def remove_egg_info(self) -> bool:
        """Removes the egg-info (editable project hook) from the folder. Returns True if we removed it."""
        if self.egg_path.exists():
            rmtree(str(self.egg_path))
            return True
        return False

    def refresh(self, environment: Optional[PythonEnvironment] = None) -> None:
        """
        Without an environment specified, the active one will be used if it exists.

        - Removes the egg-info folder from the source
        - Calls `poetry lock` if there were changes to pyproject.toml
        - Creates/Installs/Cleans the environment with remove-untracked
        """
        self.remove_egg_info()
        self.lock_if_needed()
        self.install(environment=environment, remove_untracked=True)

    def lock_if_needed(self) -> bool:
        """Lock if needed, return True if ran."""
        if not self.lock_path.exists() or self.lock_is_outdated:
            self.poetry_run("lock", breakout_of_venv=True)
            return True
        return False

    def poetry_run(
        self,
        *commands: Any,
        capture_output: bool = False,
        breakout_of_venv: bool = True,
        environment: PythonEnvironment = None,
    ) -> Optional[str]:
        """
        Internal run-a-poetry-command.

        The `environment` param will make that environment active (e.g.: `poetry env use` called before).
        """
        environment_variables = os.environ.copy()
        if breakout_of_venv:
            environment_variables.pop("VIRTUAL_ENV", None)

        with self._activate_poetry_environment(environment):
            return check_run(
                *find_python_tool(PythonTool.Poetry, environment=environment),
                *commands,
                "-vv" if self.verbose else "",
                working_directory=self.project_path,
                capture_output=capture_output,
                verbose=self.verbose,
                env=environment_variables,
            )

    @contextmanager
    def _activate_poetry_environment(
        self, environment: PythonEnvironment = None
    ) -> Generator[None, None, None]:
        """Context manager that can be used to run a block of code in a particular environment."""
        if not environment:
            # `self.activated_environment` uses us without an environment specified; prevents infinite recursion
            yield
            return

        current_environment = self.activated_environment
        if current_environment == environment:
            yield
            return

        try:
            self.poetry_run("env", "use", environment.python_executable)
            yield
        finally:
            if current_environment:
                self.poetry_run("env", "use", current_environment.python_executable)

    def __str__(self) -> str:
        return f"{self.package.name} [{self.toml_path}]"
