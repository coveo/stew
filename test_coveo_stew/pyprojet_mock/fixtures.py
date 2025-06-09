from os import PathLike
from pathlib import Path
from shutil import copytree, rmtree

import pytest
from cleo.io.null_io import NullIO

from coveo_stew.stew import PythonProject

MOCK_FOLDER = Path("mock-pyproject")
MOCK_DEPENDENCY_FOLDER = Path("mock-pyproject-dependency")
MOCK_GROUPS_FOLDER = Path("mock-poetry-groups")


@pytest.fixture
def pyproject_mock(tmpdir: PathLike) -> PythonProject:
    """This is a project with a local dependency"""
    return prepare_mock_project(MOCK_FOLDER, MOCK_DEPENDENCY_FOLDER, tmpdir=tmpdir)


@pytest.fixture
def poetry_groups_mock(tmpdir: PathLike) -> PythonProject:
    """This is a project with group dependencies"""
    return prepare_mock_project(MOCK_GROUPS_FOLDER, tmpdir=tmpdir)


def prepare_mock_project(main_project: Path, *subprojects: Path, tmpdir: PathLike) -> PythonProject:
    tmpdir = Path(tmpdir)  # I don't like PathLike and friends.

    # copy mock folders
    for mock_folder in (main_project, *subprojects):
        venv = mock_folder / ".venv"
        if venv.exists():
            rmtree(venv)
        mock_source = Path(__file__).parent / mock_folder
        assert mock_source.is_dir()
        temp_mock_folder = tmpdir / mock_folder
        copytree(mock_source, temp_mock_folder)

    # rename any mock.pyproject.toml files
    for pyproject_file in tmpdir.rglob("mock.pyproject.toml"):
        pyproject_file.rename(pyproject_file.with_name("pyproject.toml"))

    # the main project's is provided, not the dependency mock.
    return PythonProject(NullIO(), tmpdir / main_project)
