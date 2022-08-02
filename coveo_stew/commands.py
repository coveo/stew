"""Automates poetry operations in the repo."""

import re
from pathlib import Path
from typing import Generator, Iterable, List, Set, Union

import click
from coveo_functools.finalizer import finalizer
from coveo_styles.styles import ExitWithFailure, echo, install_pretty_exception_hook
from coveo_systools.filesystem import find_repo_root

from coveo_stew.discovery import discover_pyprojects, find_pyproject
from coveo_stew.exceptions import (
    CheckFailed,
    PythonProjectNotFound,
    RequirementsOutdated,
)
from coveo_stew.offline_publish import offline_publish
from coveo_stew.pydev import is_pydev_project, pull_and_write_dev_requirements
from coveo_stew.stew import (
    EnvironmentCreationBehavior,
    PythonEnvironment,
    PythonProject,
)

_COMMANDS_THAT_SKIP_INTRO_EMOJIS = ["locate"]


def _echo_updated(updated: Set[Path]) -> None:
    """Used to print updated paths to the user."""
    if updated:
        echo.outcome("Updated:", pad_before=True)
        for updated_path in sorted(updated):
            if updated_path.is_absolute():
                # try to get a relative version of this path to beautify output.
                try:
                    updated_path = updated_path.relative_to(find_repo_root(default="."))
                except ValueError:
                    ...
            echo.noise(updated_path, item=True)


def _pull_dev_requirements(
    dry_run: bool = False, verbose: bool = False
) -> Generator[Path, None, None]:
    """Writes the dev-dependencies of pydev projects' local dependencies into pydev's pyproject.toml file."""
    dry_run_text = "(dry run) " if dry_run else ""
    for pydev_project in discover_pyprojects(predicate=is_pydev_project, verbose=verbose):
        echo.step(f"Analyzing dev requirements for {pydev_project}")
        if pull_and_write_dev_requirements(pydev_project, dry_run=dry_run):
            echo.outcome(
                f"{dry_run_text}Updated {pydev_project.package.name} with new dev requirements."
            )
            if not dry_run:
                echo.outcome("Lock file and virtual environment updated !!thumbs_up!!\n")
            yield pydev_project.toml_path
        else:
            echo.success(f"{pydev_project.package.name}'s dev requirements were up to date.")


@click.group()
@click.pass_context
def stew(ctx: click.Context) -> None:
    """The 'stew' cli entry point."""
    install_pretty_exception_hook()
    if ctx.invoked_subcommand not in _COMMANDS_THAT_SKIP_INTRO_EMOJIS:
        echo.step("!!sparkles!! !!snake!! !!sparkles!!")


@stew.command()
@click.option("--verbose", is_flag=True, default=False)
def check_outdated(verbose: bool = False) -> None:
    """Return error code 1 if toml/lock are not in sync."""
    echo.step("Analyzing all pyproject.toml files and artifacts:")
    outdated: Set[Path] = set()
    try:
        for project in discover_pyprojects(verbose=verbose):
            echo.noise(project, item=True)
            if not project.lock_path.exists() or project.lock_is_outdated():
                outdated.add(project.lock_path)
    except PythonProjectNotFound as exception:
        raise ExitWithFailure from exception

    try:
        outdated.update(_pull_dev_requirements(dry_run=True, verbose=verbose))
    except PythonProjectNotFound:
        pass  # no pydev projects found.

    if outdated:
        raise ExitWithFailure(
            failures=outdated,
            suggestions='Run "poetry run pyproject fix-outdated" to update all outdated files.',
        ) from RequirementsOutdated(f"Found {len(outdated)} outdated file(s).")

    echo.success("Check complete! All files are up-to-date.")


@stew.command()
@click.option("--verbose", is_flag=True, default=False)
def fix_outdated(verbose: bool = False) -> None:
    """Scans the whole repo and updates outdated pyproject-related files.

    Updates:
        - Lock files, only if their pyproject.toml was updated.
    """
    echo.step("Synchronizing all outdated lock files:")
    updated: Set[Path] = set()
    with finalizer(_echo_updated, updated):
        try:
            for project in discover_pyprojects(verbose=verbose):
                echo.noise(project, item=True)
                if project.lock_if_needed():
                    updated.add(project.lock_path)
            try:
                updated.update(_pull_dev_requirements(dry_run=False, verbose=verbose))
            except PythonProjectNotFound:
                pass  # no pydev projects found
        except PythonProjectNotFound as exception:
            raise ExitWithFailure from exception

    echo.success(f'Update complete! {len(updated) or "No"} file(s) were modified.\n')


@stew.command()
@click.option("--verbose", is_flag=True, default=False)
def bump(verbose: bool = False) -> None:
    """Bumps locked versions for all pyprojects."""
    updated: Set[Path] = set()
    with finalizer(_echo_updated, updated):
        try:
            for project in discover_pyprojects(verbose=verbose):
                echo.step(f"Bumping {project.lock_path}")
                if project.bump():
                    updated.add(project.toml_path)
        except PythonProjectNotFound as exception:
            raise ExitWithFailure from exception

    echo.success(f'Bump complete! {len(updated) or "No"} file(s) were modified.')


@stew.command()
@click.argument("project_name")
@click.option("--directory", default=None)
@click.option("--python", default=None)
@click.option("--verbose", is_flag=True, default=False)
def build(
    project_name: str,
    directory: Union[str, Path] = None,
    python: Union[str, Path] = None,
    verbose: bool = False,
) -> None:
    """
    Store all dependencies of a python project into a local directory, according to its poetry.lock,
    for later use with `--find-links` and `--no-index`.

    --directory:
        IF unspecified and repo:    "repo_root/.wheels/*.whl"
        IF unspecified and no repo: "pyproject_folder/.wheels/*.whl"
        IF specified:               "directory/*.whl"
    """
    try:
        project = find_pyproject(project_name, verbose=verbose)
    except PythonProjectNotFound as exception:
        raise ExitWithFailure from exception

    python_environments = (
        [PythonEnvironment(python)]
        if python
        else project.virtual_environments(
            create_default_if_missing=EnvironmentCreationBehavior.Empty
        )
    )

    if not directory:
        directory = (project.repo_root or project.project_path) / ".wheels"
    assert directory
    directory = Path(directory)

    echo.step(f"Building python project {project} in {directory}")
    for environment in python_environments:
        echo.outcome(f"virtual environment: {environment}", pad_before=True)
        offline_publish(project, directory, environment)

    echo.success()


@stew.command()
@click.argument("project_name", default=None, required=False)
@click.option("--verbose", is_flag=True, default=False)
def fresh_eggs(project_name: str = None, verbose: bool = False) -> None:
    """
    Removes the egg-info from project folders.

    If launched from a folder containing a "pydev" project and "install" is true, reinstall
    the virtual environment (which recreates the egg-info).

    The egg-info is the "editable" install of your project. It allows you to modify the code between
    runs without reinstalling.

    Some behaviors (such as console entrypoints) are bootstrapped into the egg-info at install time, and
    won't be updated between runs. This is when this tool comes in handy.
    """
    echo.step("Removing *.egg-info folders.")
    deleted = False
    try:
        for project in discover_pyprojects(query=project_name, verbose=verbose):
            if project.remove_egg_info():
                echo.outcome("Deleted: ", project.egg_path, item=True)
                deleted = True
    except PythonProjectNotFound as exception:
        raise ExitWithFailure from exception

    if deleted:
        echo.suggest("Environments were not refreshed. You may want to call 'poetry install'.")

    echo.success()


@stew.command()
@click.option("--dry-run/--no-dry-run", default=False)
@click.option("--verbose", is_flag=True, default=False)
def pull_dev_requirements(dry_run: bool = False, verbose: bool = False) -> None:
    """Writes the dev-dependencies of pydev projects' local dependencies into pydev's pyproject.toml file."""
    try:
        list(_pull_dev_requirements(dry_run=dry_run, verbose=verbose))
    except PythonProjectNotFound as exception:
        raise ExitWithFailure from exception


def _beautify_mypy_output(
    project: PythonProject, output: Iterable[str], *, full_paths: bool = False
) -> None:
    """Main use: guide IDEs by showing full paths to the files vs the current working directory.
    Bonus: highlight errors in red and display a slightly shortened version of the error output."""
    pattern = re.compile(
        rf"^(?P<path>{project.package.safe_name}.+):(?P<line>\d+):(?P<column>\d+(?::)| )"
        rf"(?:\s?error:\s?)(?P<detail>.+)$"
    )
    for line in output:
        match = pattern.fullmatch(line)
        if match:
            adjusted_path = project.project_path / Path(match["path"])
            adjusted_path = (
                adjusted_path.resolve()
                if full_paths
                else adjusted_path.relative_to(Path(".").resolve())
            )
            echo.error_details(
                f'{adjusted_path}:{match["line"]}:{match["column"]} {match["detail"]}'
            )
        else:
            echo.noise(line)


@stew.command()
@click.argument("project_name")
@click.option("--verbose", is_flag=True, default=False)
def locate(project_name: str, verbose: bool = False) -> None:
    """Locate a python project (in the whole git repo) and print the directory containing the pyproject.toml file."""
    try:
        echo.passthrough(find_pyproject(project_name, verbose=verbose).project_path)
    except PythonProjectNotFound as exception:
        # check for partial matches to guide the user
        partial_matches = (
            project.package.name
            for project in discover_pyprojects(query=project_name, verbose=verbose)
        )
        try:
            raise ExitWithFailure(
                suggestions=(
                    "Exact match required but partial matches were found:",
                    *partial_matches,
                )
            ) from exception
        except PythonProjectNotFound:
            # we can't find a single project to suggest; raise the original exception.
            raise ExitWithFailure from exception


@stew.command()
@click.argument("project_name", default=None, required=False)
@click.option("--exact-match/--no-exact-match", default=False)
@click.option("--verbose", is_flag=True, default=False)
def refresh(project_name: str = None, exact_match: bool = False, verbose: bool = False) -> None:
    echo.step("Refreshing python project environments...")
    pydev_projects = []
    try:
        for project in discover_pyprojects(
            query=project_name, exact_match=exact_match, verbose=verbose
        ):
            if project.options.pydev:
                pydev_projects.append(project)
                continue  # do these at the end
            echo.normal(project, pad_before=True, pad_after=True, emoji="hourglass")
            project.refresh()
    except PythonProjectNotFound as exception:
        raise ExitWithFailure from exception

    for project in pydev_projects:
        echo.normal(project, pad_before=True, pad_after=True, emoji="hourglass")
        if project.current_environment_belongs_to_project():
            echo.warning(f"Cannot update {project} because it's what we're currently running.")
        else:
            project.refresh()

    echo.success()


@stew.command()
@click.argument("project_name", default=None, required=False)
@click.option("--exact-match/--no-exact-match", default=False)
@click.option("--fix/--no-fix", default=False)
@click.option("--check", multiple=True, default=None)
@click.option("--skip", multiple=True, default=None)
@click.option("--verbose", is_flag=True, default=False)
@click.option(
    "--quick",
    is_flag=True,
    default=False,
    help="Do not call 'poetry install --remove-untracked' before testing.",
)
@click.option("--parallel/--sequential", default=True)
def ci(
    project_name: str = None,
    exact_match: bool = False,
    fix: bool = False,
    check: List[str] = None,
    skip: List[str] = None,
    verbose: bool = False,
    quick: bool = False,
    parallel: bool = True,
) -> None:
    failures = []
    try:
        for project in discover_pyprojects(
            query=project_name, exact_match=exact_match, verbose=verbose
        ):
            echo.step(project.package.name, pad_after=False)
            if not project.launch_continuous_integration(
                auto_fix=fix, checks=check, skips=skip, quick=quick, parallel=parallel
            ):
                failures.append(project)
    except PythonProjectNotFound as exception:
        raise ExitWithFailure from exception

    if failures:
        raise ExitWithFailure(failures=failures) from CheckFailed(
            f"{len(failures)} project(s) failed ci steps."
        )
