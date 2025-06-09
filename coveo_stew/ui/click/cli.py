"""Automates poetry operations in the repo."""

import sys
from pathlib import Path
from typing import Any, Final, Optional, Tuple, Union

import click
from cleo.io.inputs.argv_input import ArgvInput
from cleo.io.io import IO
from cleo.io.outputs.output import Verbosity
from cleo.io.outputs.stream_output import StreamOutput
from coveo_styles.styles import ExitWithFailure, echo, install_pretty_exception_hook
from packaging.version import Version

from coveo_stew import commands

# The `deprecated` parameter for click.option was introduced in Click 8.2.0
CLICK_LEGACY = Version(click.__version__) < Version("8.2.0")
CLICK_DEPRECATED: dict[str, Any] = {} if CLICK_LEGACY else {"deprecated": True}

_COMMANDS_THAT_SKIP_INTRO_EMOJIS = ["locate", "version"]

PROJECT_NAME_ARG: Final = click.argument("project_name", default=None, required=False)
EXACT_MATCH_ARG: Final = click.option("--exact-match/--no-exact-match", default=False)
VERBOSE_ARG: Final = click.option("--verbose", "-v", is_flag=True, default=False)
NO_CACHE_ARG: Final = click.option(
    "--no-cache",
    is_flag=True,
    default=False,
    help="Adds `--no-cache` to all poetry commands.",
)


def create_io(verbose: bool = False) -> IO:
    """
    Creates and returns a cleo IO instance for command interaction.

    Args:
        verbose: Whether to set verbose output mode

    Returns:
        A properly configured IO instance
    """

    input_instance = ArgvInput()
    output_instance = StreamOutput(sys.stdout)
    error_output_instance = StreamOutput(sys.stderr)

    io = IO(input_instance, output_instance, error_output_instance)

    # Set verbosity based on the verbose flag
    if verbose:
        io.set_verbosity(Verbosity.VERBOSE)
    else:
        io.set_verbosity(Verbosity.NORMAL)

    return io


@click.group()
@click.pass_context
def stew(ctx: click.Context) -> None:
    """The 'stew' cli entry point."""
    install_pretty_exception_hook()
    if ctx.invoked_subcommand not in _COMMANDS_THAT_SKIP_INTRO_EMOJIS:
        echo.step("!!sparkles!! !!snake!! !!sparkles!!")


@stew.command()
@VERBOSE_ARG
def version(verbose: bool = False) -> None:
    """Prints the version of the coveo-stew package."""
    commands.version(io=create_io(verbose))


@stew.command()
@PROJECT_NAME_ARG
@EXACT_MATCH_ARG
@VERBOSE_ARG
@NO_CACHE_ARG
def check_outdated(
    project_name: Optional[str] = None,
    exact_match: bool = False,
    verbose: bool = False,
    no_cache: bool = False,
) -> None:
    """Return error code 1 if toml/lock are not in sync."""
    commands.check_outdated(
        io=create_io(verbose),
        project_name=project_name,
        exact_match=exact_match,
        verbose=verbose,
        disable_cache=no_cache,
    )


@stew.command()
@PROJECT_NAME_ARG
@EXACT_MATCH_ARG
@VERBOSE_ARG
@NO_CACHE_ARG
def fix_outdated(
    project_name: Optional[str] = None,
    exact_match: bool = False,
    verbose: bool = False,
    no_cache: bool = False,
) -> None:
    """Scans the whole repo and updates outdated pyproject-related files.

    Updates:
        - Lock files, only if their pyproject.toml was updated.
    """
    commands.fix_outdated(
        io=create_io(verbose),
        project_name=project_name,
        exact_match=exact_match,
        verbose=verbose,
        disable_cache=no_cache,
    )


@stew.command()
@PROJECT_NAME_ARG
# Unlike all other commands, exact match is true by default to retain
# the original behavior which required a project name to be specified exactly.
@click.option("--exact-match/--no-exact-match", default=True)
@VERBOSE_ARG
@click.option(
    "--directory", default=None, help="Deprecated: use --target instead.", **CLICK_DEPRECATED
)
@click.option("--target", default=None, help="Directory where the built wheels should be stored.")
@click.option("--python", default=None, help="The python executable to use.")
@NO_CACHE_ARG
def build(
    project_name: Optional[str] = None,
    exact_match: bool = True,
    directory: Union[str, Path] = None,
    target: Union[str, Path] = None,
    python: Union[str, Path] = None,
    verbose: bool = False,
    no_cache: bool = False,
) -> None:
    """
    Store all dependencies of a python project into a local directory, according to its poetry.lock,
    for later use with `--find-links` and `--no-index`.

    --target:
        IF unspecified and repo:    "repo_root/.wheels/*.whl"
        IF unspecified and no repo: "pyproject_folder/.wheels/*.whl"
        IF specified:               "directory/*.whl"
    """
    if not project_name:
        exact_match = False  # if you write `stew build` we build all.

    target = (
        target or directory
    )  # Use target if provided, otherwise fallback to deprecated directory

    commands.build(
        io=create_io(verbose),
        project_name=project_name,
        exact_match=exact_match,
        directory=target,
        python=python,
        verbose=verbose,
        disable_cache=no_cache,
    )


@stew.command()
@PROJECT_NAME_ARG
@EXACT_MATCH_ARG
@VERBOSE_ARG
def fresh_eggs(
    project_name: str = None,
    exact_match: bool = False,
    verbose: bool = False,
    no_cache: bool = False,
) -> None:
    """
    Removes the egg-info from project folders.

    If launched from a folder containing a "pydev" project and "install" is true, reinstall
    the virtual environment (which recreates the egg-info).

    The egg-info is the "editable" install of your project. It allows you to modify the code between
    runs without reinstalling.

    Some behaviors (such as console entrypoints) are bootstrapped into the egg-info at install time, and
    won't be updated between runs. This is when this tool comes in handy.
    """
    commands.fresh_eggs(
        io=create_io(verbose),
        project_name=project_name,
        exact_match=exact_match,
        verbose=verbose,
        disable_cache=no_cache,
    )


@stew.command()
@click.option("--dry-run/--no-dry-run", default=False)
@VERBOSE_ARG
@NO_CACHE_ARG
def pull_dev_requirements(
    dry_run: bool = False, verbose: bool = False, no_cache: bool = False
) -> None:
    """Writes the dev-dependencies of pydev projects' local dependencies into pydev's pyproject.toml file."""
    commands.pull_dev_requirements(
        io=create_io(verbose), dry_run=dry_run, verbose=verbose, disable_cache=no_cache
    )


@stew.command()
@click.argument("project_name")
@click.option("--verbose", is_flag=True, default=False)
@NO_CACHE_ARG
def locate(project_name: str, verbose: bool = False, no_cache: bool = False) -> None:
    """Locate a python project (in the whole git repo) and print the directory containing the pyproject.toml file."""
    commands.locate(
        io=create_io(verbose), project_name=project_name, verbose=verbose, disable_cache=no_cache
    )


@stew.command()
@PROJECT_NAME_ARG
@EXACT_MATCH_ARG
@VERBOSE_ARG
@NO_CACHE_ARG
def refresh(
    project_name: str = None,
    exact_match: bool = False,
    verbose: bool = False,
    no_cache: bool = False,
) -> None:
    """Refresh python project environments."""
    commands.refresh(
        io=create_io(verbose),
        project_name=project_name,
        exact_match=exact_match,
        verbose=verbose,
        disable_cache=no_cache,
    )


@stew.command()
@PROJECT_NAME_ARG
@EXACT_MATCH_ARG
@VERBOSE_ARG
@click.option("--fix", is_flag=True, help="Fix issues found during CI checks where possible.")
@click.option(
    "--check",
    multiple=True,
    default=(),
    help="Specify which checks to run (e.g., pytest, black, mypy).",
)
@click.option("--skip", multiple=True, default=(), help="Specify which checks to skip.")
@click.option(
    "--quick",
    is_flag=True,
    default=False,
    help="Do not call 'poetry install --sync' before testing.",
)
@click.option(
    "--parallel",
    is_flag=True,
    help="Deprecated: Use --sequential to disable parallel checks.",
    **CLICK_DEPRECATED,
)
@click.option("--sequential", is_flag=True, help="Run checks sequentially instead of in parallel.")
@click.option(
    "--github-step-report",
    is_flag=True,
    default=False,
    envvar="GITHUB_ACTIONS",
    help="Generate GitHub step report output.",
)
@click.option(
    "--extra", multiple=True, default=(), help="Additional extras to include when testing."
)
@click.option("--no-extras", is_flag=True, help="Don't use any extras when testing.")
@click.option("--all-extras", is_flag=True, help="Use all extras when testing.")
@NO_CACHE_ARG
def ci(
    project_name: str = None,
    exact_match: bool = False,
    fix: bool = False,
    check: Tuple[str, ...] = (),
    skip: Tuple[str, ...] = (),
    verbose: bool = False,
    quick: bool = False,
    parallel: bool = True,
    sequential: bool = False,
    github_step_report: bool = False,
    extra: Tuple[str, ...] = (),
    no_extras: bool = False,
    all_extras: bool = False,
    no_cache: bool = False,
) -> None:
    """Run continuous integration steps on Python projects."""

    if parallel and sequential:
        raise ExitWithFailure(
            suggestions=[
                "Checks run in parallel by default.",
                "Use --sequential to run checks sequentially.",
                "The --parallel option is deprecated and does nothing anymore.",
            ],
        ) from ValueError("Both --parallel and --sequential were specified.")

    commands.ci(
        create_io(verbose),
        project_name,
        exact_match=exact_match,
        fix=fix,
        check=check,
        skip=skip,
        verbose=verbose,
        quick=quick,
        parallel=not sequential,
        github_step_report=github_step_report,
        extra=extra,
        no_extras=no_extras,
        all_extras=all_extras,
        disable_cache=no_cache,
    )


@stew.command()
@PROJECT_NAME_ARG
@EXACT_MATCH_ARG
@VERBOSE_ARG
@NO_CACHE_ARG
def bump(
    project_name: Optional[str] = None,
    exact_match: bool = False,
    verbose: bool = False,
    no_cache: bool = False,
) -> None:
    """Bumps locked versions."""
    commands.bump(
        io=create_io(verbose),
        project_name=project_name,
        exact_match=exact_match,
        verbose=verbose,
        disable_cache=no_cache,
    )
