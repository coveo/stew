from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from cleo.io.null_io import NullIO
from coveo_styles.styles import ExitWithFailure

from coveo_stew.ci.mypy_runner import MypyRunner


@pytest.fixture
def tmp_project(tmp_path: Path) -> MagicMock:
    """Fixture to provide a dummy Python project in a temp directory as a MagicMock."""
    project = MagicMock()
    project.project_path = tmp_path
    project.verbose = False
    project.virtual_environments.return_value = []
    return project


@pytest.mark.parametrize(
    "check_paths,skip_paths",
    [
        (["foo"], ["bar"]),
        ("foo", "bar"),
        ("foo", ["bar"]),
        (["foo"], "bar"),
    ],
)
def test_check_and_skip_paths_mutually_exclusive(
    tmp_project: MagicMock, check_paths: list[str] | str, skip_paths: list[str] | str
) -> None:
    """Test that check_paths and skip_paths cannot be used together."""
    with pytest.raises(ExitWithFailure, match="cannot be used together"):
        MypyRunner(
            NullIO(),
            check_paths=check_paths,
            skip_paths=skip_paths,
            set_config=False,
            _pyproject=tmp_project,
        )


def test_check_paths_must_be_relative(tmp_project: MagicMock) -> None:
    """Test that check_paths must be relative paths."""
    abs_path: str = str(Path(".").absolute())
    # Patch _validate_typed_package to skip py.typed check
    with patch.object(MypyRunner, "_validate_typed_package", MagicMock()):
        with pytest.raises(ExitWithFailure, match="contains absolute paths"):
            MypyRunner(NullIO(), check_paths=[abs_path], set_config=False, _pyproject=tmp_project)


def test_skip_paths_must_be_relative(tmp_project: MagicMock) -> None:
    """Test that skip_paths must be relative paths."""
    abs_path: str = str(Path(".").absolute())
    with pytest.raises(ExitWithFailure, match="contains absolute paths"):
        MypyRunner(NullIO(), skip_paths=[abs_path], set_config=False, _pyproject=tmp_project)


def test_check_paths_must_have_py_typed(tmp_project: MagicMock) -> None:
    """Test that check_paths must point to a directory containing a py.typed file."""
    pkg: Path = tmp_project.project_path / "foo"
    pkg.mkdir()
    # Should fail if py.typed is missing
    with pytest.raises(ExitWithFailure, match="No py.typed file found"):
        MypyRunner(NullIO(), check_paths=["foo"], set_config=False, _pyproject=tmp_project)
    # Should succeed if py.typed exists
    (pkg / "py.typed").touch()
    try:
        MypyRunner(NullIO(), check_paths=["foo"], set_config=False, _pyproject=tmp_project)
    except ExitWithFailure:
        pytest.fail("Should not raise when py.typed exists")
