from pathlib import Path
from typing import Callable, Generator

from coveo_styles.styles import echo
from coveo_systools.filesystem import find_paths, find_repo_root

from coveo_stew.exceptions import NotAPoetryProject, PythonProjectNotFound
from coveo_stew.metadata.python_api import PythonFile
from coveo_stew.stew import PythonProject

Predicate = Callable[[PythonProject], object]


def find_pyproject(project_name: str, path: Path = None, *, verbose: bool = False) -> PythonProject:
    """Find a python project in path using the exact project name"""
    project = next(
        discover_pyprojects(path, query=project_name, exact_match=True, verbose=verbose), None
    )
    if not project:
        raise PythonProjectNotFound(f"{project_name} cannot be found in {path}")
    return project


def discover_pyprojects(
    path: Path = None,
    *,
    query: str = None,
    exact_match: bool = False,
    verbose: bool = False,
    predicate: Predicate = None,
) -> Generator[PythonProject, None, None]:
    """
    Search for Python projects in a path and return PythonProject instances.

    Parameters:
        path: where to start looking for pyproject.toml files. Default: git root or '.'
        query: substring for package selection. '-' and '_' are equivalent. case insensitive.
        exact_match: turns query into an exact match. Recommended use: CI scripts
        verbose: output more details to command line
        predicate: optional inclusion filter
    """
    if not path:
        path = find_repo_root(default=".")

    if exact_match and not query:
        raise PythonProjectNotFound("An exact match was requested but no query was provided.")

    predicate = predicate or (lambda _: True)
    paths = find_paths(PythonFile.PyProjectToml, search_from=path, in_children=True, in_root=True)

    count_projects = 0
    for file in paths:
        try:
            project = PythonProject(file, verbose=verbose)
        except NotAPoetryProject:
            continue

        if verbose:
            echo.noise("PyProject found: ", project)

        if predicate(project) and (
            not query
            or (exact_match and project.package.name == query)
            or (
                not exact_match
                and query.replace("-", "_").lower() in project.package.safe_name.lower()
            )
        ):
            count_projects += 1
            yield project

    if count_projects == 0:
        raise PythonProjectNotFound(
            f"Cannot find any project that could match {query}"
            if query
            else "No python projects were found."
        )
