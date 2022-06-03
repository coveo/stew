from pathlib import Path
from typing import Callable, Any

from coveo_testing.markers import UnitTest
from toml.decoder import TomlDecodeError

from coveo_stew.utils import _load_toml_from_content


DUMMY_TEST_PATH = Path("/some/dummy/path.toml")


def _retrieve_exception(
    fn: Callable = _load_toml_from_content, *args: Any, **kwargs: Any
) -> Exception:
    try:
        fn(*args, **kwargs)
    except Exception as exception:
        return exception

    assert False, "Did not raise."


@UnitTest
def test_toml_decode_error() -> None:
    exception = _retrieve_exception(_load_toml_from_content, """invalid""", DUMMY_TEST_PATH)
    assert isinstance(exception.__cause__, TomlDecodeError)
    error_line = 1
    error_col = 8
    assert f"{DUMMY_TEST_PATH}:{error_line}:{error_col}" in str(exception)


@UnitTest
def test_toml_repeated_section() -> None:
    toml = """\
    [tool.poetry]
    name = "coveo-grab-bag"
    version = "0.0.6"
    description = "Grab bag of infinite utilities."
    authors = ["Jonathan piché <tools@coveo.com>"]

    [tool.poetry]
    python = ">=3.6"
    """
    error_line = 7
    error_col = 1
    exception = _retrieve_exception(_load_toml_from_content, toml, DUMMY_TEST_PATH)
    assert isinstance(exception.__cause__, TomlDecodeError)
    assert f"{DUMMY_TEST_PATH}:{error_line}:{error_col}" in str(exception)
    assert "already exists" in str(exception)  # may change with new toml parser versions
