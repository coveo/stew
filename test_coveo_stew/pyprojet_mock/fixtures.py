from os import PathLike
from pathlib import Path
from shutil import copytree, rmtree

import pytest

from coveo_stew.stew import PythonProject


MOCK_FOLDER = Path("mock-pyproject")
MOCK_DEPENDENCY_FOLDER = Path("mock-pyproject-dependency")


@pytest.fixture
def pyproject_mock(tmpdir: PathLike) -> PythonProject:
    tmpdir = Path(tmpdir)  # I don't like PathLike and friends.

    # copy mock folders
    for mock_folder in MOCK_FOLDER, MOCK_DEPENDENCY_FOLDER:
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
    return PythonProject(tmpdir / MOCK_FOLDER)
