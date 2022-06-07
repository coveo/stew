import logging
import os
import re
from pathlib import Path
from tempfile import mkstemp
from typing import Optional, Pattern, Set

from coveo_styles.styles import ExitWithFailure
from coveo_systools.platforms import WINDOWS
from coveo_systools.subprocess import check_output

from coveo_stew.discovery import find_pyproject
from coveo_stew.environment import PythonEnvironment, PythonTool
from coveo_stew.exceptions import LockNotFound, PythonProjectNotFound
from coveo_stew.stew import PythonProject

_DEFAULT_PIP_OPTIONS = (
    "--disable-pip-version-check",
    "--no-input",
    "--exists-action",
    "i",
    "--pre",
)

# looks like:
# - `coveo-stew @ file://home/jonapich/code/stew/coveo-stew; python ...` on linux
# - `coveo-stew @ file:///C:/Users/jonapich/code/stew/coveo-stew; python ...` on windows :shrug:
if WINDOWS:
    LOCAL_REQUIREMENT_PATTERN: Pattern = re.compile(
        r"^(?P<library_name>.+) @ file:///(?P<path>.+);"
    )
else:
    LOCAL_REQUIREMENT_PATTERN = re.compile(r"^(?P<library_name>.+) @ file://(?P<path>.+);")


def offline_publish(
    project: PythonProject,
    wheelhouse: Path,
    environment: PythonEnvironment,
    *,
    quiet: bool = False,
) -> None:
    """
    Store the project and all its locked dependencies into a folder, so that it can be installed offline using pip.

    Some packages provide wheels specific to an interpreter's version/abi/platform/implementation. It's important
    to use the right environment here because the files may differ and `pip install --no-index` will not work.
    """
    try:
        _OfflinePublish(project, wheelhouse, environment).perform_offline_install(quiet=quiet)
    except LockNotFound as exception:
        raise ExitWithFailure(
            suggestions="Run `stew bump` or `poetry lock` and try again."
        ) from exception


class _OfflinePublish:
    """Handles the offline publish."""

    def __init__(
        self, project: PythonProject, wheelhouse: Path, environment: PythonEnvironment
    ) -> None:
        self.project = project
        self.environment = environment
        self.wheelhouse = wheelhouse
        self._valid_packages: Optional[Set[str]] = None
        self._local_projects: Set[str] = {
            name
            for (name, package) in self.project.package.all_dependencies.items()
            if package.path
        }

    @property
    def verbose(self) -> bool:
        return self.project.verbose

    def perform_offline_install(self, *, quiet: bool = False) -> None:
        """Performs all the operation for the offline install."""
        if not self.project.lock_path.exists():
            raise LockNotFound("Project isn't locked; can't proceed.")

        # build the wheels for the current project
        self.project.build(self.wheelhouse)
        self._store_setup_dependencies_in_wheelhouse()
        self._store_dependencies_in_wheelhouse()

        # validate the wheelhouse; this will exit in error if something's amiss or result in a noop if all is right.
        self._validate_package(f"{self.project.package.name}=={self.project.package.version}")

    def _store_setup_dependencies_in_wheelhouse(
        self, project: Optional[PythonProject] = None
    ) -> None:
        """store the build dependencies in the wheelhouse, like setuptools.
        Eventually pip/poetry will play better and this won't be necessary anymore"""
        project = project or self.project

        for dependency in project.options.build_dependencies.values():
            dep = (
                dependency.name
                if dependency.version == "*"
                else f"{dependency.name}{dependency.version}"
            )  # such as setuptools>=42
            _ = check_output(
                *self.environment.build_command(PythonTool.Pip, "wheel", dep),
                working_directory=self.wheelhouse,
                verbose=self.verbose,
            )

    def _store_dependencies_in_wheelhouse(self, project: Optional[PythonProject] = None) -> None:
        """Store the dependency wheels in the wheelhouse."""
        project = project or self.project

        lines = []
        for requirement in project.export().splitlines():
            if match := LOCAL_REQUIREMENT_PATTERN.match(requirement):
                dependency_name, dependency_location = match["library_name"], Path(match["path"])
                # this is a local dependency. Since poetry locks all transitive dependencies,
                # we're only interested in the setup dependencies and the local dependency.
                try:
                    dependency = find_pyproject(dependency_name, path=dependency_location)
                except PythonProjectNotFound as exception:
                    raise ExitWithFailure(
                        failures=f"There was no poetry project for {dependency_name} in {dependency_location}"
                    ) from exception
                self._store_setup_dependencies_in_wheelhouse(dependency)
                dependency.build(self.wheelhouse)
            else:
                # keep the line as is.
                lines.append(requirement)

        requirements_file_descriptor, requirements_file_path = mkstemp()
        with os.fdopen(requirements_file_descriptor, mode="w+") as f:
            f.write("\n".join(lines))

        command = self.environment.build_command(
            PythonTool.Pip,
            "wheel",
            "--wheel-dir",
            self.wheelhouse,
            "--no-deps",
            "--no-cache-dir",
            "--requirement",
            requirements_file_path,
            *_DEFAULT_PIP_OPTIONS,
        )

        try:
            _ = check_output(*command, verbose=self.verbose)
        finally:
            try:
                Path(requirements_file_path).unlink(missing_ok=True)
            except Exception:  # noqa
                logging.exception(f"Cannot delete {requirements_file_path}. Ignoring.")

    def _validate_package(self, package_specification: str) -> None:
        """Validates that a package and all its dependencies can be resolved from the wheelhouse.
        Package specification can be a name like `coveo-functools` or a constraint like `coveo-functools>=0.2.1`"""
        # using check_output will silence output
        _ = check_output(
            *self.environment.build_command(
                PythonTool.Pip,
                "wheel",
                package_specification,
                "--find-links",
                self.wheelhouse,
                "--wheel-dir",
                self.wheelhouse,
                "--no-index",
                *_DEFAULT_PIP_OPTIONS,
            ),
            working_directory=self.wheelhouse,
            verbose=self.verbose,
        )
