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
from typing import (
    Any,
    Final,
    Generator,
    Iterator,
    List,
    Optional,
    Pattern,
    Tuple,
    Union,
)

from coveo_functools.casing import flexfactory
from coveo_itertools.lookups import dict_lookup
from coveo_systools.filesystem import CannotFindRepoRoot, find_repo_root
from coveo_systools.subprocess import check_run

from coveo_stew.environment import PythonEnvironment, PythonTool, find_python_tool
from coveo_stew.exceptions import NotAPoetryProject, StewException
from coveo_stew.metadata.poetry_api import PoetryAPI
from coveo_stew.metadata.python_api import PythonFile
from coveo_stew.metadata.stew_api import StewPackage
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

    def relative_path(self, path: Path) -> Path:
        """returns the relative path of a path vs the project folder."""
        return path.relative_to(self.project_path)

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
        self, *, create_default_if_missing: Union[bool, EnvironmentCreationBehavior] = False
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
        if install is EnvironmentCreationBehavior.Full:
            self.poetry_run("install")
        elif install is EnvironmentCreationBehavior.NoDev:
            self.poetry_run("install", "--no-dev")
        else:
            assert install is EnvironmentCreationBehavior.Empty
            self.poetry_run("env", "use", "python")

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
                yield Path(match.groupdict()["path"].strip()), bool(
                    match.groupdict().get("activated")
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
            raise StewException(
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
        command = ["export"]
        if self.options.build_without_hashes:
            command.append("--without-hashes")

        return self.poetry_run(*command, capture_output=True)

    def launch_continuous_integration(
        self,
        auto_fix: bool = False,
        checks: Optional[List[str]] = None,
        skips: Optional[List[str]] = None,
        quick: bool = False,
        parallel: bool = True,
    ) -> bool:
        """Launch all continuous integration runners on the project."""
        return asyncio.run(
            self.ci.launch_continuous_integration(
                auto_fix=auto_fix, checks=checks, skips=skips, quick=quick, parallel=parallel
            )
        )

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
        target_environment = environment or self.activated_environment()
        if not target_environment:
            self._create_default_poetry_install()
            return

        if target_environment.installed:
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
        target_environment.installed = True
        target_environment.cleaned |= remove_untracked

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
        if not self.lock_path.exists() or self.lock_is_outdated():
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
        return f"{self.package.name} [{self.toml_path}]"
