from coveo_stew.stew import PythonProject
from test_coveo_stew.pyprojet_mock.fixtures import poetry_groups_mock

_ = poetry_groups_mock


def test_poetry_groups(poetry_groups_mock: PythonProject) -> None:
    assert set(poetry_groups_mock.package.dependencies) == {
        "python",
        "requests",
        "black",
    }  # black is in extra
    assert set(poetry_groups_mock.package.dev_dependencies) == {"mypy"}
    assert set(poetry_groups_mock.package.all_dependencies) == {
        "python",
        "requests",
        "black",
        "mypy",
    }
