from pathlib import Path
from typing import Callable, Generator, Optional

from cleo.io.io import IO
from cleo.io.outputs.output import Verbosity
from coveo_styles.styles import echo
from coveo_systools.filesystem import find_paths, find_repo_root
from poetry.core.pyproject.exceptions import PyProjectError
from poetry.factory import Factory
from poetry.poetry import Poetry

from coveo_stew.exceptions import PythonProjectNotFound
from coveo_stew.metadata.python_api import PythonFile
from coveo_stew.stew import PythonProject

Predicate = Callable[[Poetry], object]


def find_pyproject(
    io: IO, project_name: str, path: Path = None, *, verbose: bool = False
) -> PythonProject:
    """Find a python project in path using the exact project name"""
    project = next(
        discover_pyprojects(io, path, query=project_name, exact_match=True, verbose=verbose),
        None,
    )
    if not project:
        raise PythonProjectNotFound(f"{project_name} cannot be found in {path}")
    return project


def discover_pyprojects(
    io: IO,
    path: Path = None,
    *,
    query: Optional[str] = None,
    exact_match: bool = False,
    verbose: bool = False,
    predicate: Optional[Predicate] = None,
    find_nested: bool = True,
    disable_cache: bool = False,
) -> Generator[PythonProject, None, None]:
    """
    Search for Python projects in a path and return PythonProject instances.

    Parameters:
        path: where to start looking for pyproject.toml files. Default: git root or '.'
        query: Name of the project:
          - case-insensitive
          - Substring match if exact_match is false.
          - '-' and '_' are equivalent.
        exact_match: turns query into an exact match. Recommended use: CI scripts
        verbose: output more details to command line
        predicate: optional inclusion filter
        find_nested: search in subdirectories
        disable_cache: Will configure the execution to pass `--no-cache` to poetry.
    """
    assert isinstance(io, IO)
    if not path:
        path = find_repo_root(default=".")

    if exact_match and not query:
        raise PythonProjectNotFound("An exact match was requested but no query was provided.")

    predicate = predicate or (lambda _: True)
    paths = find_paths(
        PythonFile.PyProjectToml, search_from=path, in_children=find_nested, in_root=True
    )

    count_projects = 0
    for file in paths:
        try:
            io.write_line(f"Found: {file}", verbosity=Verbosity.VERBOSE)
            poetry = Factory().create_poetry(
                cwd=file.parent,
                io=io,
                disable_plugins=False,
                disable_cache=disable_cache,
            )
        except PyProjectError as ex:
            # this will inform the user which pyproject.toml files were found and skipped
            if verbose:
                echo.noise("Skipping: ", ex, emoji="information")
            continue

        if verbose:
            echo.noise("PyProject found: ", poetry)

        if predicate(poetry) and (
            not query
            or (exact_match and poetry.package.pretty_name == query)
            or (not exact_match and query.replace("-", "_").lower() in poetry.package.name.lower())
        ):
            count_projects += 1
            yield PythonProject(io, poetry, verbose=verbose, disable_cache=disable_cache)

    if count_projects == 0:
        raise PythonProjectNotFound(
            f"Cannot find any project that could match {query}"
            if query
            else "No python projects were found."
        )
