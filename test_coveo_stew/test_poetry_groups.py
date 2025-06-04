from coveo_stew.stew import PythonProject
from test_coveo_stew.pyprojet_mock.fixtures import poetry_groups_mock

_ = poetry_groups_mock


def test_poetry_groups(poetry_groups_mock: PythonProject) -> None:
    # when users call `pip install`, they don't get the groups.
    # `extras` should be used instead of groups since groups aren't meant to be used with `pip install`.
    assert set(d.pretty_name for d in poetry_groups_mock.dependencies) == {"requests"}

    # calling `poetry install` will install all the groups; stew considers groups as dev dependencies.
    assert set(d.pretty_name for d in poetry_groups_mock.dev_dependencies) == {"mypy", "black"}

    # all dependencies, including groups.
    assert set(d.pretty_name for d in poetry_groups_mock.all_dependencies) == {
        "requests",
        "black",
        "mypy",
    }
