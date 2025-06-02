from pathlib import Path
from textwrap import dedent
from typing import Iterable, Optional

import pytest
from _pytest.tmpdir import TempPathFactory
from cleo.io.null_io import NullIO
from coveo_testing.parametrize import parametrize

from coveo_stew.ci.mypy_runner import MypyRunner
from coveo_stew.metadata.python_api import PythonFile
from coveo_stew.stew import PythonProject


def create_mock_project(tmp_path_factory: TempPathFactory) -> PythonProject:
    """Create a mock Python project for testing."""
    project_dir = tmp_path_factory.mktemp("mock_project")
    (project_dir / "pyproject.toml").write_text(
        dedent(
            """
        [project]
        name = "mock-project"
        version = "0.1.0"
        description = "Mock project for testing"
        authors = [
            {name = "Test", email = "test@example.com"}
        ]
        requires-python = ">=3.9,<4"

        [build-system]
        requires = ["setuptools >= 61.0.0"]
        build-backend = "setuptools.build_meta"
        """
        )
    )
    return PythonProject(NullIO(), project_dir)


def create_folder_structure(
    project_path: Path, typed_folders: Iterable[str], untyped_folders: Iterable[str]
) -> None:
    """
    Create a folder structure with py.typed files in specified paths.

    Args:
        project_path: The root project path
        typed_folders: List of relative paths where py.typed files should be placed
        untyped_folders: List of relative paths to create without py.typed files
    """
    # Create folders with py.typed files
    for folder in typed_folders:
        folder_path = project_path / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        (folder_path / PythonFile.TypedPackage).touch()

    # Create folders without py.typed files
    for folder in untyped_folders:
        folder_path = project_path / folder
        folder_path.mkdir(parents=True, exist_ok=True)


@parametrize(
    "typed_folders, untyped_folders, expected_folders",
    [
        # Test case 1: Single top-level typed folder
        ({"pkg1"}, set(), {"pkg1"}),
        # Test case 2: Multiple top-level typed folders
        ({"pkg1", "pkg2"}, set(), {"pkg1", "pkg2"}),
        # Test case 3: Nested typed folders - should only return parent
        ({"pkg1", "pkg1/subpkg"}, set(), {"pkg1"}),
        # Test case 4: Complex nested structure
        (
            {"pkg1", "pkg1/subpkg1", "pkg2", "pkg2/subpkg1", "pkg3/subpkg1"},
            set(),
            {"pkg1", "pkg2", "pkg3/subpkg1"},
        ),
        # Test case 5: Sibling folders should both be found
        ({"pkg1/subpkg1", "pkg1/subpkg2"}, set(), {"pkg1/subpkg1", "pkg1/subpkg2"}),
        # Test case 6: Deeply nested folders
        (
            {"pkg1/sub1/subsub1", "pkg1/sub2/subsub1", "pkg2/sub1"},
            set(),
            {"pkg1/sub1/subsub1", "pkg1/sub2/subsub1", "pkg2/sub1"},
        ),
        # Test case 7: Empty case
        (set(), set(), set()),
        # Test case 8: Mixed typed and untyped folders
        (
            {"pkg1", "pkg3/subpkg1"},
            {"pkg2", "pkg3", "pkg4/subpkg1"},
            {"pkg1", "pkg3/subpkg1"},
        ),
        # Test case 9: Untyped parent with typed child
        (
            {"pkg1/sub1"},
            {"pkg1", "pkg2"},
            {"pkg1/sub1"},
        ),
        # Test case 10: Only untyped folders
        (
            set(),
            {"pkg1", "pkg2", "pkg3/subpkg1"},
            set(),
        ),
        # Test case 11: Mixed nested typed/untyped folders
        (
            {"pkg1", "pkg2/sub1/subsub2"},
            {"pkg2", "pkg2/sub1", "pkg2/sub2", "pkg1/sub1"},
            {"pkg1", "pkg2/sub1/subsub2"},
        ),
    ],
)
def test_find_typed_folders(
    tmp_path_factory: TempPathFactory,
    typed_folders: set[str],
    untyped_folders: set[str],
    expected_folders: set[str],
) -> None:
    """Test that _find_typed_folders correctly identifies typed folders."""
    # Create mock project
    project = create_mock_project(tmp_path_factory)

    # Create the folder structure with typed and untyped folders
    create_folder_structure(project.project_path, typed_folders, untyped_folders)

    # Create the MypyRunner
    runner = MypyRunner(NullIO(), _pyproject=project)

    # Get the results from _find_typed_folders
    found_folders = set(runner._find_typed_folders())

    # Convert found paths to strings relative to project path for easier comparison
    found_folder_names = {
        folder.relative_to(project.project_path).as_posix() for folder in found_folders
    }

    # Assert the expected folders were found
    assert (
        found_folder_names == expected_folders
    ), f"Expected folders {expected_folders}, but found {found_folder_names}"


def test_check_paths_override(tmp_path_factory: TempPathFactory) -> None:
    """Test that providing check_paths overrides the automatic typed folder detection."""
    # Create mock project
    project = create_mock_project(tmp_path_factory)

    # Create a folder structure with typed and untyped folders
    typed_folders = {"pkg1", "pkg2", "pkg3"}
    create_folder_structure(project.project_path, typed_folders, ())

    def _test(check_paths: Optional[list[str]]) -> set[str]:
        runner = MypyRunner(NullIO(), check_paths=check_paths, _pyproject=project)
        found_folders = set(runner._find_typed_folders())
        assert all(
            folder.is_absolute() for folder in found_folders
        ), "All found folders should be absolute paths"
        return {folder.relative_to(project.project_path).as_posix() for folder in found_folders}

    # Validate that the automatic detection finds all typed folders
    expected_all_paths = {"pkg1", "pkg2", "pkg3"}
    assert _test(None) == expected_all_paths
    assert _test([]) == expected_all_paths

    # Validate that the check_paths override will exclude pkg2
    expected_subset = {"pkg1", "pkg3"}
    result = _test(["pkg1", "pkg3"])
    assert result == expected_subset


def test_skip_paths_functionality(tmp_path_factory: TempPathFactory) -> None:
    """Test that skip_paths correctly excludes specified paths from type checking."""
    # Create mock project
    project = create_mock_project(tmp_path_factory)

    # Create a folder structure with typed folders
    typed_folders = {"pkg1", "pkg2/subpkg", "pkg3", "pkg4/subpkg"}
    create_folder_structure(project.project_path, typed_folders, ())

    # Create the MypyRunner with skip_paths
    runner = MypyRunner(NullIO(), skip_paths=["pkg1", "pkg4"], _pyproject=project)

    # Get the results from _find_typed_folders
    found_folders = set(runner._find_typed_folders())

    # Convert found paths to strings relative to project path for easier comparison
    found_folder_names = {
        folder.relative_to(project.project_path).as_posix() for folder in found_folders
    }

    # We expect to find only the typed folders that aren't in skip_paths
    # Both pkg1 and pkg4 folders (and subfolders) should be skipped
    expected_folder_set = {"pkg2/subpkg", "pkg3"}

    # Assert the expected folders were found
    assert (
        found_folder_names == expected_folder_set
    ), f"Expected folders {expected_folder_set}, but found {found_folder_names}"


def test_check_paths_and_skip_paths_mutually_exclusive(tmp_path_factory: TempPathFactory) -> None:
    """Test that check_paths and skip_paths cannot be used together."""
    # Create mock project
    project = create_mock_project(tmp_path_factory)

    # This should raise a ValueError
    with pytest.raises(ValueError):
        MypyRunner(NullIO(), check_paths="yes", skip_paths="yes", _pyproject=project)
