from unittest import mock

from coveo_systools.subprocess import check_output
from coveo_testing.mocks import ref
from coveo_testing.parametrize import parametrize
from packaging.version import Version

from coveo_stew.environment import _find_poetry_version


@parametrize(
    ["poetry_output", "expected_version"],
    (
        ("Poetry version 1.1.15\n", "1.1.15"),
        ("Poetry (version 1.2.2)", "1.2.2"),
        ("Fiction Poetry 🐍 [Version: 777.7.77]", "777.7.77"),
    ),
)
def test_poetry_version(poetry_output: str, expected_version: str) -> None:
    with mock.patch(*ref(check_output, context=_find_poetry_version), return_value=poetry_output):
        assert _find_poetry_version(None) == Version(expected_version)
