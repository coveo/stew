from os import PathLike
from pathlib import Path
from textwrap import dedent

import pytest
from cleo.io.null_io import NullIO
from coveo_testing.parametrize import parametrize
from poetry.poetry import Poetry

from coveo_stew.discovery import discover_pyprojects, find_pyproject
from coveo_stew.exceptions import PythonProjectNotFound


def create_mock_pyproject(parent_dir: Path, project_name: str, version: str = "0.1.0") -> Path:
    """Create a minimal mock pyproject.toml file and return its directory."""
    project_dir = parent_dir / project_name
    project_dir.mkdir(parents=True, exist_ok=True)

    pyproject_content = dedent(
        f"""\
        [project]
        name = "{project_name}"
        version = "{version}"
        description = "Mock project for testing"
        authors = [
            {{name = "Test", email = "test@example.com"}}
        ]
        requires-python = ">=3.9,<4"
        """
    )

    (project_dir / "pyproject.toml").write_text(pyproject_content)
    return project_dir


def test_discover_pyprojects_no_query_returns_all(tmpdir: PathLike) -> None:
    """When no query is provided, all projects should be returned."""
    tmp_path = Path(tmpdir)
    create_mock_pyproject(tmp_path, "project-one")
    create_mock_pyproject(tmp_path, "project-two")
    create_mock_pyproject(tmp_path, "another-lib")

    projects = list(discover_pyprojects(NullIO(), tmp_path))

    assert len(projects) == 3
    project_names = {p.poetry.package.pretty_name for p in projects}
    assert project_names == {"project-one", "project-two", "another-lib"}


def test_discover_pyprojects_empty_directory_raises(tmpdir: PathLike) -> None:
    """When no projects exist, PythonProjectNotFound should be raised."""
    tmp_path = Path(tmpdir)

    with pytest.raises(PythonProjectNotFound, match="No python projects were found"):
        list(discover_pyprojects(NullIO(), tmp_path))


def test_discover_pyprojects_query_no_match_raises(tmpdir: PathLike) -> None:
    """When query doesn't match any project, PythonProjectNotFound should be raised."""
    tmp_path = Path(tmpdir)
    create_mock_pyproject(tmp_path, "my-project")

    with pytest.raises(
        PythonProjectNotFound, match="Cannot find any project that could match nonexistent"
    ):
        list(discover_pyprojects(NullIO(), tmp_path, query="nonexistent"))


@parametrize(
    ["query", "expected_match"],
    [
        ("proj", True),  # substring match
        ("project", True),  # full word match
        ("my", True),  # prefix match
        ("ject", True),  # suffix match
        ("xyz", False),  # no match
    ],
)
def test_discover_pyprojects_substring_matching(
    tmpdir: PathLike, query: str, expected_match: bool
) -> None:
    """Query should perform substring matching when exact_match is False."""
    tmp_path = Path(tmpdir)
    create_mock_pyproject(tmp_path, "my-project")

    if expected_match:
        projects = list(discover_pyprojects(NullIO(), tmp_path, query=query))
        assert len(projects) == 1
        assert projects[0].poetry.package.pretty_name == "my-project"
    else:
        with pytest.raises(PythonProjectNotFound):
            list(discover_pyprojects(NullIO(), tmp_path, query=query))


@parametrize(
    ["query"],
    [
        ("MY-PROJECT",),
        ("My-Project",),
        ("my-project",),
        ("MY-PROJ",),  # substring, case-insensitive
    ],
)
def test_discover_pyprojects_case_insensitive(tmpdir: PathLike, query: str) -> None:
    """Query matching should be case-insensitive."""
    tmp_path = Path(tmpdir)
    create_mock_pyproject(tmp_path, "my-project")

    projects = list(discover_pyprojects(NullIO(), tmp_path, query=query))
    assert len(projects) == 1
    assert projects[0].poetry.package.pretty_name == "my-project"


@parametrize(
    ["project_name", "query"],
    [
        ("my-project", "my_project"),
        ("my_project", "my-project"),
        ("my-lib-name", "my_lib_name"),
        ("test_package", "test-package"),
    ],
)
def test_discover_pyprojects_hyphen_underscore_normalization(
    tmpdir: PathLike, project_name: str, query: str
) -> None:
    """Hyphens and underscores should be treated as equivalent in queries."""
    tmp_path = Path(tmpdir)
    create_mock_pyproject(tmp_path, project_name)

    projects = list(discover_pyprojects(NullIO(), tmp_path, query=query))
    assert len(projects) == 1
    assert projects[0].poetry.package.pretty_name == project_name


def test_discover_pyprojects_exact_match_success(tmpdir: PathLike) -> None:
    """With exact_match=True, only projects with matching pretty_name should be returned."""
    tmp_path = Path(tmpdir)
    create_mock_pyproject(tmp_path, "my-project")
    create_mock_pyproject(tmp_path, "my-project-extended")

    projects = list(discover_pyprojects(NullIO(), tmp_path, query="my-project", exact_match=True))

    assert len(projects) == 1
    assert projects[0].poetry.package.pretty_name == "my-project"


def test_discover_pyprojects_exact_match_no_match_raises(tmpdir: PathLike) -> None:
    """With exact_match=True and non-matching query, PythonProjectNotFound should be raised."""
    tmp_path = Path(tmpdir)
    create_mock_pyproject(tmp_path, "my-project")

    with pytest.raises(
        PythonProjectNotFound, match="Cannot find any project that could match other-project"
    ):
        list(discover_pyprojects(NullIO(), tmp_path, query="other-project", exact_match=True))


def test_discover_pyprojects_exact_match_without_query_raises(tmpdir: PathLike) -> None:
    """With exact_match=True but no query, PythonProjectNotFound should be raised."""
    tmp_path = Path(tmpdir)
    create_mock_pyproject(tmp_path, "my-project")

    with pytest.raises(
        PythonProjectNotFound, match="An exact match was requested but no query was provided"
    ):
        list(discover_pyprojects(NullIO(), tmp_path, exact_match=True))


def test_discover_pyprojects_find_nested_true(tmpdir: PathLike) -> None:
    """With find_nested=True, projects in subdirectories should be found."""
    tmp_path = Path(tmpdir)
    create_mock_pyproject(tmp_path, "root-project")

    # Create nested project
    nested_dir = tmp_path / "subdir"
    nested_dir.mkdir()
    create_mock_pyproject(nested_dir, "nested-project")

    projects = list(discover_pyprojects(NullIO(), tmp_path, find_nested=True))

    assert len(projects) == 2
    project_names = {p.poetry.package.pretty_name for p in projects}
    assert project_names == {"root-project", "nested-project"}


def test_discover_pyprojects_find_nested_false(tmpdir: PathLike) -> None:
    """With find_nested=False, only root-level projects should be found."""
    tmp_path = Path(tmpdir)

    # Create root project directly in search path (not in a subdirectory)
    (tmp_path / "pyproject.toml").write_text(
        dedent(
            """\
        [project]
        name = "root-project"
        version = "0.1.0"
        description = "Mock project for testing"
        authors = [
            {name = "Test", email = "test@example.com"}
        ]
        requires-python = ">=3.9,<4"
        """
        )
    )

    # Create nested project in subdirectory
    nested_dir = tmp_path / "subdir"
    nested_dir.mkdir()
    create_mock_pyproject(nested_dir, "nested-project")

    projects = list(discover_pyprojects(NullIO(), tmp_path, find_nested=False))

    assert len(projects) == 1
    assert projects[0].poetry.package.pretty_name == "root-project"


def test_discover_pyprojects_with_predicate_filter(tmpdir: PathLike) -> None:
    """Predicate should filter projects based on Poetry metadata."""
    tmp_path = Path(tmpdir)
    create_mock_pyproject(tmp_path, "project-v1", version="1.0.0")
    create_mock_pyproject(tmp_path, "project-v2", version="2.0.0")
    create_mock_pyproject(tmp_path, "project-v1-another", version="1.5.0")

    # Filter only version 2.x projects
    def predicate(p: Poetry) -> bool:
        return p.package.version.text.startswith("2.")

    projects = list(discover_pyprojects(NullIO(), tmp_path, predicate=predicate))

    assert len(projects) == 1
    assert projects[0].poetry.package.pretty_name == "project-v2"
    assert projects[0].poetry.package.version.text == "2.0.0"


def test_discover_pyprojects_with_predicate_and_query(tmpdir: PathLike) -> None:
    """Predicate and query should work together to filter projects."""
    tmp_path = Path(tmpdir)
    create_mock_pyproject(tmp_path, "my-project", version="1.0.0")
    create_mock_pyproject(tmp_path, "my-other-project", version="2.0.0")
    create_mock_pyproject(tmp_path, "different-lib", version="1.0.0")

    # Filter by version and name
    def predicate(p: Poetry) -> bool:
        return p.package.version.text.startswith("1.")

    projects = list(discover_pyprojects(NullIO(), tmp_path, query="my", predicate=predicate))

    assert len(projects) == 1
    assert projects[0].poetry.package.pretty_name == "my-project"


def test_discover_pyprojects_predicate_excludes_all_raises(tmpdir: PathLike) -> None:
    """When predicate excludes all projects, PythonProjectNotFound should be raised."""
    tmp_path = Path(tmpdir)
    create_mock_pyproject(tmp_path, "project-v1", version="1.0.0")

    # Predicate that excludes everything
    def predicate(_p: Poetry) -> bool:
        return False

    with pytest.raises(PythonProjectNotFound, match="No python projects were found"):
        list(discover_pyprojects(NullIO(), tmp_path, predicate=predicate))


def test_discover_pyprojects_invalid_pyproject_skipped(tmpdir: PathLike) -> None:
    """Invalid pyproject.toml files should be skipped gracefully."""
    tmp_path = Path(tmpdir)
    create_mock_pyproject(tmp_path, "valid-project")

    # Create invalid pyproject.toml
    invalid_dir = tmp_path / "invalid-project"
    invalid_dir.mkdir()
    (invalid_dir / "pyproject.toml").write_text("invalid { toml content")

    projects = list(discover_pyprojects(NullIO(), tmp_path))

    # Only the valid project should be found
    assert len(projects) == 1
    assert projects[0].poetry.package.pretty_name == "valid-project"


def test_find_pyproject_exact_match_success(tmpdir: PathLike) -> None:
    """find_pyproject should return the exact matching project."""
    tmp_path = Path(tmpdir)
    create_mock_pyproject(tmp_path, "target-project")
    create_mock_pyproject(tmp_path, "other-project")

    project = find_pyproject(NullIO(), "target-project", tmp_path)

    assert project.poetry.package.pretty_name == "target-project"


def test_find_pyproject_not_found_raises(tmpdir: PathLike) -> None:
    """find_pyproject should raise when project is not found."""
    tmp_path = Path(tmpdir)
    create_mock_pyproject(tmp_path, "some-project")

    with pytest.raises(
        PythonProjectNotFound, match="Cannot find any project that could match nonexistent"
    ):
        find_pyproject(NullIO(), "nonexistent", tmp_path)


def test_discover_pyprojects_multiple_matches_with_query(tmpdir: PathLike) -> None:
    """When query matches multiple projects, all should be returned."""
    tmp_path = Path(tmpdir)
    create_mock_pyproject(tmp_path, "my-project-one")
    create_mock_pyproject(tmp_path, "my-project-two")
    create_mock_pyproject(tmp_path, "other-lib")

    projects = list(discover_pyprojects(NullIO(), tmp_path, query="my-project"))

    assert len(projects) == 2
    project_names = {p.poetry.package.pretty_name for p in projects}
    assert project_names == {"my-project-one", "my-project-two"}
