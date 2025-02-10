from unittest import mock

from coveo_testing.mocks import ref
from coveo_testing.parametrize import parametrize
from packaging.version import Version

from coveo_stew.environment import find_poetry_version
from coveo_stew.poetry_backward_compatibility import get_install_sync_command, get_verb


@parametrize(
    ["poetry_version", "verb", "expected_verb"],
    (
        ("0.0.1", "--anything", "--anything"),
        ("0.0.1", "--sync", "--remove-untracked"),
        ("1.1.15", "--sync", "--remove-untracked"),  # last 1.1.x version as of writing
        (
            "1.1.16",
            "--sync",
            "--remove-untracked",
        ),  # if they bugfix we still need to use the deprecated word
        ("1.2.0", "--sync", "--sync"),  # first version with deprecation
        ("1.2.1", "--sync", "--sync"),
        ("2.24.2", "--sync", "--sync"),
        ("3.0.0", "--anything", "--anything"),
    ),
)
def test_get_verb(poetry_version: str, verb: str, expected_verb: str) -> None:
    with mock.patch(
        *ref(find_poetry_version, context=get_verb),
        return_value=Version(poetry_version),
    ):
        get_verb.cache_clear()
        assert get_verb(verb, None) == expected_verb


@parametrize(
    ["poetry_version", "expected_command"],
    (
        ("0.0.1", ["install", "--remove-untracked"]),
        ("1.1.15", ["install", "--remove-untracked"]),
        ("1.1.16", ["install", "--remove-untracked"]),  # unreleased, would be a hotfix
        ("1.2.0", ["install", "--sync"]),
        ("2.0.0", ["sync"]),
        ("3.0.0", ["sync"]),  # unreleased at time of writing
    ),
)
def test_get_install_sync_command(poetry_version: str, expected_command: str) -> None:
    with mock.patch(
        *ref(find_poetry_version, context=get_install_sync_command),
        return_value=Version(poetry_version),
    ):
        get_verb.cache_clear()
        assert get_install_sync_command(None) == expected_command
