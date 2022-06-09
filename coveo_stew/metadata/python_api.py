from pathlib import Path

from typing_extensions import Final


class PythonFile:
    """Well-known python filenames."""

    PyProjectToml: Final[Path] = Path("pyproject.toml")  # https://www.python.org/dev/peps/pep-0518/
    PoetryLock: Final[Path] = Path("poetry.lock")
    TypedPackage: Final[Path] = Path("py.typed")  # https://www.python.org/dev/peps/pep-0561/
