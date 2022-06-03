from os import PathLike
from pathlib import Path
from textwrap import dedent

from coveo_systools.filesystem import pushd
from coveo_testing.markers import UnitTest, Integration
from coveo_testing.parametrize import parametrize
from poetry.core.packages import Package
import pytest

from coveo_stew.exceptions import NotAPoetryProject
from coveo_stew.offline_publish import offline_publish
from coveo_stew.stew import PythonProject

from test_coveo_stew.pyprojet_mock.fixtures import pyproject_mock

_ = pyproject_mock  # mark the fixture as used


@UnitTest
def test_pyproject_mock_initial_state(pyproject_mock: PythonProject) -> None:
    """A few basic checks on the project's initial state."""
    assert pyproject_mock.project_path.exists()
    assert pyproject_mock.lock_path.exists()
    assert pyproject_mock.toml_path.exists()
    assert not pyproject_mock.egg_path.exists()
    assert pyproject_mock.repo_root is None  # not a git root


@Integration
def test_pyproject_mock_initial_state_integration(pyproject_mock: PythonProject) -> None:
    assert not pyproject_mock.lock_is_outdated


@UnitTest
@parametrize("package_name", ("requests", "mock-pyproject-dependency"))
def test_pyproject_dependencies(pyproject_mock: PythonProject, package_name: str) -> None:
    dependency = pyproject_mock.package.dependencies[package_name]
    assert dependency.version == "*"
    assert dependency.name == package_name
    assert not dependency.optional
    assert not dependency.extras


@UnitTest
def test_pyproject_locker(pyproject_mock: PythonProject) -> None:
    locked_requests: Package = next(
        filter(
            lambda package: package.name == "requests",
            pyproject_mock.poetry.locker.locked_repository().packages,
        )
    )
    assert str(locked_requests.version) == "2.26.0"


@Integration
def test_pyproject_virtual_environment(pyproject_mock: PythonProject) -> None:
    assert not list(pyproject_mock.virtual_environments())
    assert not pyproject_mock.current_environment_belongs_to_project()
    assert len(list(pyproject_mock.virtual_environments(create_default_if_missing=True))) == 1


@Integration
def test_pyproject_publish(pyproject_mock: PythonProject, tmpdir: PathLike) -> None:
    pyproject_mock.install()
    publish_location = Path(tmpdir) / "local-publish"
    assert not publish_location.exists()
    with pushd(Path(tmpdir)):
        # note: local directories are found from working folder or git root
        offline_publish(
            pyproject_mock,
            publish_location,
            next(pyproject_mock.virtual_environments(create_default_if_missing=True)),
        )
    assert publish_location.exists()

    # note: the package names in the filenames end up as underscores, not dashes.
    for required_file in (
        "setuptools",
        "setuptools_scm",
        "requests",
        "wheel",
        "mock_pyproject_dependency",
        "black",
    ):
        assert any(publish_location.rglob(f"{required_file}-*")), f"Cannot find {required_file}"


@UnitTest
def test_toml_not_a_poetry_project(tmp_path: Path) -> None:
    assert tmp_path.exists()
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        dedent(
            """\
    [tool.flit]
    foo = "bar"

    [tool.stew.ci]
    mypy = false
    """
        )
    )
    with pytest.raises(NotAPoetryProject):
        _ = PythonProject(pyproject)
