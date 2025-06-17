"""Interact with python projects programmatically."""

import asyncio
import os
import re
import shutil
import sys
from contextlib import contextmanager
from enum import Enum, auto
from functools import cached_property
from pathlib import Path
from shutil import rmtree
from subprocess import CalledProcessError
from typing import (
    Any,
    Final,
    Generator,
    Iterable,
    Iterator,
    List,
    Optional,
    Pattern,
    Tuple,
    Union,
)

from cleo.io.io import IO
from coveo_functools import flex
from coveo_functools.casing import flexfactory
from coveo_systools.filesystem import CannotFindRepoRoot, find_repo_root
from coveo_systools.subprocess import check_run
from poetry.factory import Factory
from poetry.poetry import Poetry

from coveo_stew.ci.runner_status import RunnerStatus
from coveo_stew.config import load_config_from_presets
from coveo_stew.environment import PythonEnvironment, PythonTool, find_python_tool
from coveo_stew.exceptions import NotAPoetryProject, StewException, UsageError
from coveo_stew.metadata.stew_api import StewPackage
from coveo_stew.poetry_backward_compatibility import get_install_sync_command
from coveo_stew.utils import load_toml_from_path

ENVIRONMENT_PATH_PATTERN: Final[Pattern] = re.compile(
    r"^(?P<path>.+?)(?: (?P<activated>\(Activated\)))?$"
)


class EnvironmentCreationBehavior(Enum):
    Full = auto()
    NoDev = auto()
    Empty = auto()


class PythonProject:
    """Access the information within a pyproject.toml file and operate on them."""

    def __init__(
        self,
        io: IO,
        poetry: Union[Poetry, Path],
        *,
        verbose: bool = False,
        disable_cache: bool = False,
    ) -> None:
        self.io = io
        self.verbose = verbose

        if isinstance(poetry, Path):
            try:
                self.poetry = Factory().create_poetry(
                    cwd=poetry.parent if poetry.is_file() else poetry,
                    io=io,
                    disable_plugins=False,
                    disable_cache=disable_cache,
                )
            except RuntimeError as ex:
                raise NotAPoetryProject(poetry) from ex
        else:
            self.poetry = poetry

        self.project_path = self.poetry.pyproject_path.parent

        self.dependencies = set(self.poetry.package.requires)
        self.all_dependencies = set(self.poetry.package.all_requires)
        self.dev_dependencies = self.all_dependencies - self.dependencies

        toml_content = load_toml_from_path(self.poetry.pyproject_path)

        self.egg_path: Path = self.project_path / f"{self.poetry.package.name}.egg-info"

        stew_config, ci_config = load_config_from_presets(io, toml_content)
        self.options = flex.deserialize(stew_config, hint=StewPackage, errors="raise")

        from coveo_stew.ci.config import ContinuousIntegrationConfig  # circular import

        if self.options.pydev:
            # ensure no steps are repeated. pydev projects only receive basic poetry/lock checks
            self.ci: ContinuousIntegrationConfig = ContinuousIntegrationConfig(
                check_outdated=True,
                poetry_check=True,
                mypy=False,
                _pyproject=self,
                io=self.io,
            )
        else:
            self.ci = flexfactory(
                ContinuousIntegrationConfig, **ci_config, io=self.io, _pyproject=self
            )

        try:
            repo_root: Optional[Path] = find_repo_root(self.project_path)
        except CannotFindRepoRoot:
            repo_root = None

        self.repo_root: Optional[Path] = repo_root

    @cached_property
    def _virtual_environments_cache(self) -> List[PythonEnvironment]:
        cache: List[PythonEnvironment] = []

        for path, activated in self._get_virtual_environment_paths():
            environment = PythonEnvironment(path)
            cache.append(environment)
            environment.activated = activated

        if cache and not any(environment.activated for environment in cache):
            self.poetry_run("env", "use", cache[0].python_executable)
            cache[0].activated = True

        return cache

    def overrides_from_cli(
        self, extras: Tuple[str, ...] = (), no_extras: bool = False, all_extras: bool = False
    ) -> None:
        """Overrides the project's options with the CLI arguments."""
        if no_extras and (extras or all_extras):
            raise UsageError("Cannot use --no-extras with --extras or --all-extras.")
        if all_extras and (extras or no_extras):
            raise UsageError("Cannot use --all-extras with --extras or --no-extras.")

        if extras:
            self.options.extras = list(extras)
            self.options.all_extras = False
        if no_extras:
            self.options.extras = []
            self.options.all_extras = False
        if all_extras:
            self.options.extras = []
            self.options.all_extras = True

    def relative_path(self, path: Path) -> Path:
        """returns the relative path of a path vs the project folder."""
        return path.relative_to(self.project_path)

    def lock_is_outdated(self) -> bool:
        """True if the toml file has pending changes that were not applied to poetry.lock"""
        if not self.poetry.locker.is_locked():
            return False

        # yolo: use the dry run output to determine if the lock is too old
        dry_run_output = self.poetry_run(
            *get_install_sync_command(self.activated_environment()),
            "--dry-run",
            capture_output=True,
        )

        for sentence in (
            "poetry.lock is not consistent with pyproject.toml",  # poetry 1.2.2
            "Warning: The lock file is not up to date",
            "outdated dependencies",
            "Run update to update them",
        ):
            if sentence.casefold() in dry_run_output.casefold():
                return True

        return False

    def activated_environment(self) -> Optional[PythonEnvironment]:
        """The environment activated for a project.

        Note: cached for performance, could theoretically become out-of-sync with reality, either due to a bug,
        or because someone called `poetry env use` while we were working :shrug:

        To prevent out of sync:
            - Use the context manager `self._activate_poetry_environment`
            - or use the `environment` argument of `self.poetry_run`
        """
        if not self._virtual_environments_cache:
            return None

        return next(
            environment for environment in self._virtual_environments_cache if environment.activated
        )

    def virtual_environments(
        self,
        *,
        create_default_if_missing: Union[bool, EnvironmentCreationBehavior] = False,
    ) -> Iterator[PythonEnvironment]:
        """The project's virtual environments. These are cached for performance.

        create_default_if_missing: When no environments are found, install the environment using what poetry
            would use by default.
        """
        if not self._virtual_environments_cache and create_default_if_missing:
            behavior = (
                EnvironmentCreationBehavior.Full
                if create_default_if_missing is True
                else create_default_if_missing
            )
            self._create_default_poetry_install(behavior)

        yield from self._virtual_environments_cache

    def _create_default_poetry_install(
        self, install: EnvironmentCreationBehavior = EnvironmentCreationBehavior.Full
    ) -> PythonEnvironment:
        """To be used only when no environments exist. Creates a default one by calling "poetry install"."""
        command: list[str] = []
        if install is EnvironmentCreationBehavior.Full:
            command = self._generate_poetry_install_command()
        elif install is EnvironmentCreationBehavior.NoDev:
            command = self._generate_poetry_install_command()
            command.append("--no-dev")

        if command:
            self.poetry_run(*command)
        else:
            assert install is EnvironmentCreationBehavior.Empty
            try:
                self.poetry_run("env", "use", "python")
            except CalledProcessError:
                self.poetry_run("env", "use", "python3")

        del self._virtual_environments_cache  # force cache refresh
        activated_environment = self.activated_environment()

        if install is EnvironmentCreationBehavior.Full:
            activated_environment.installed = True
            activated_environment.cleaned = True

        return activated_environment

    def _get_virtual_environment_paths(self) -> Iterator[Tuple[Path, bool]]:
        """Returns tuples of (path, activated)"""
        for str_path in self.poetry_run(
            "env", "list", "--full-path", capture_output=True, breakout_of_venv=True
        ).split("\n"):
            if (stripped := str_path.strip()) and (
                match := re.fullmatch(ENVIRONMENT_PATH_PATTERN, stripped)
            ):
                yield (
                    Path(match.groupdict()["path"].strip()),
                    bool(match.groupdict().get("activated")),
                )

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
        if not self.poetry.locker.is_locked():
            return self.lock_if_needed()

        content = self.poetry.locker.lock.read_text()
        self.poetry_run("update", "--lock", breakout_of_venv=True)
        self.poetry.locker._lock_data = None
        if content != self.poetry.locker.lock.read_text():
            return True
        return False

    def build(self, target_path: Path = None) -> Path:
        """Builds the package's wheel. If a path is provided, it will be moved there.
        Returns final path to the artifact."""

        if not self.activated_environment():
            # Starting from poetry 1.2.0, when calling `poetry build` without an environment setup, it will
            # install the environment, build, but it will not show the filename to the output anymore.
            # Ensure that a default environment exists.
            self._create_default_poetry_install(install=EnvironmentCreationBehavior.Empty)

        _ = self.poetry_run("build", "--format", "wheel", capture_output=True)

        # cloudtrail_logs_firehose_ingest-0.1.0-py3-none-any.whl
        expected_distribution = self.poetry.package.name.replace("-", "_").casefold()
        expected_version = self.poetry.package.pretty_version
        # like coredump_detector-0.0.1-py3-none-any.whl
        filename_pattern = re.compile(
            rf"(?P<distribution>{re.escape(expected_distribution)})-(?P<version>{expected_version})-.+\.whl"
        )

        # there's a file that matches the expected pattern in self.wheelhouse; find it.
        wheel_match: Optional[re.Match[str]] = None
        for file in (self.project_path / "dist").glob("*.whl"):
            if file.is_file() and (match := filename_pattern.fullmatch(file.name)):
                wheel_match = match
                break

        if not wheel_match:
            raise StewException(
                f"Could not find a wheel file for {self.poetry.package.pretty_name} "
                f"version {self.poetry.package.pretty_version} in {self.project_path / 'dist'}."
            )

        # validate
        assert (
            wheel_match.group("distribution").casefold() == expected_distribution
        ), f"{wheel_match['distribution']} does not match {self.poetry.package.pretty_name}"
        assert (
            wheel_match["version"] == self.poetry.package.pretty_version
        ), f"{wheel_match['version']} does not match {self.poetry.package.pretty_version}"
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
        assert target_path.is_dir(), f"{target_path} could not be found from {Path('.').absolute()}"
        shutil.move(str(wheel), str(target))

        return target

    def export(self) -> str:
        """Generates the content of a `requirements.txt` file based on the lock."""
        command = ["export", "--with-credentials"]
        if self.options.build_without_hashes:
            command.append("--without-hashes")

        return self.poetry_run(*command, capture_output=True)

    def launch_continuous_integration(
        self,
        auto_fix: bool = False,
        checks: Optional[Iterable[str]] = None,
        skips: Optional[Iterable[str]] = None,
        quick: bool = False,
        parallel: bool = True,
        github: bool = False,
    ) -> RunnerStatus:
        """Launch all continuous integration runners on the project."""
        return asyncio.run(
            self.ci.launch_continuous_integration(
                auto_fix=auto_fix,
                checks=checks,
                skips=skips,
                quick=quick,
                parallel=parallel,
                github=github,
            )
        )

    def install(
        self,
        *,
        environment: PythonEnvironment = None,
        sync: bool = False,
        quiet: bool = False,
    ) -> None:
        """
        Performs a 'poetry install' on the project. If an environment is provided, target it.
        """
        target_environment = environment or self.activated_environment()
        if not target_environment:
            self._create_default_poetry_install()
            return

        if target_environment.installed:
            # this environment was already installed
            if not (sync and not target_environment.cleaned):
                # return unless we are cleaning a non-cleaned environment
                return

        command = self._generate_poetry_install_command(target_environment if sync else None, quiet)
        self.poetry_run(*command, environment=target_environment)
        target_environment.installed = True
        target_environment.cleaned |= sync

    def _generate_poetry_install_command(
        self, sync_target_environment: Optional[PythonEnvironment] = None, quiet: bool = False
    ) -> List[str]:
        command: List[str] = (
            get_install_sync_command(sync_target_environment)
            if sync_target_environment
            else ["install"]
        )

        if quiet and not self.verbose:
            command.append("--quiet")
        if self.options.all_extras:
            command.append("--all-extras")
        elif self.options.extras:
            for extra in self.options.extras:
                command.extend(["--extras", extra])
        return command

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
        self.install(environment=environment, sync=True)

    def lock_if_needed(self) -> bool:
        """Lock if needed, return True if ran."""
        if not (self.poetry.locker.is_locked() and self.poetry.locker.is_fresh()):
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
                "--no-cache" if self.poetry.disable_cache else "",
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

        current_environment = self.activated_environment()
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
        return f"{self.poetry.package.pretty_name} [{self.poetry.pyproject_path}]"
