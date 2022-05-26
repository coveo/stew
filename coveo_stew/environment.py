from enum import Enum
from functools import lru_cache
from pathlib import Path
import platform
import sys
from typing import Union, Optional, Any, List
from typing_extensions import Final

from coveo_systools.subprocess import check_output


RUNNING_IN_WINDOWS: bool = bool(platform.system() == "Windows")


class PythonTool(Enum):
    Python = "python"
    Poetry = "poetry"
    Mypy = "mypy"
    Pytest = "pytest"
    Pip = "pip"
    Black = "black"


class PythonEnvironment:
    """Simple class to DRY-virtualenv."""

    _prefix, _suffix = ("Scripts", ".exe") if RUNNING_IN_WINDOWS else ("bin", "")

    def __init__(self, environment_path: Union[Path, str]) -> None:
        """
        The 'environment_path' argument may either point to:
            - a python executable
            - a virtualenv folder that contains a 'bin' (linux) or 'Scripts' (windows) folder.
        """
        self._python_version: Optional[str] = None

        # code uses these to mark envs as installed/activated to cut down on steps.
        # not the cleanest way; works for now.
        self.installed: bool = False
        self.activated: bool = False
        self.cleaned: bool = False

        python_path = Path(environment_path)
        if python_path.is_dir():
            python_path = (python_path / self._prefix / "python").with_suffix(self._suffix)

        if not python_path.exists():
            raise FileNotFoundError(f"Cannot find a python executable in {environment_path}")

        self.python_executable: Path = python_path

    @lru_cache()
    def _guess_path(self, tool: Union[PythonTool, str]) -> Path:
        if tool is PythonTool.Python:
            return self.python_executable

        tool_name = tool.value if isinstance(tool, PythonTool) else tool
        return self.python_executable.with_name(tool_name).with_suffix(self._suffix).absolute()

    def build_command(self, tool: Union[PythonTool, str], *args: Any) -> List[Any]:
        """Builds a command for a python module."""
        tool = tool.value if isinstance(tool, PythonTool) else tool
        return [self.python_executable, "-m", tool, *args]

    @property
    def mypy_executable(self) -> Path:
        return self._guess_path(PythonTool.Mypy)

    @property
    def poetry_executable(self) -> Path:
        return self._guess_path(PythonTool.Poetry)

    @property
    def pytest_executable(self) -> Path:
        return self._guess_path(PythonTool.Pytest)

    @property
    def black_executable(self) -> Path:
        return self._guess_path(PythonTool.Black)

    @property
    def python_version(self) -> str:
        if self._python_version is None:
            self._python_version = check_output(str(self.python_executable), "--version").strip()
        assert self._python_version is not None
        return self._python_version

    @property
    def pretty_python_version(self) -> str:
        """Will change e.g. Python 3.6.8 into py3.6.8"""
        version = self.python_version.split(" ")[1]
        return f"py{version}"

    def __str__(self) -> str:
        try:
            return f"{self.python_version} ({self.python_executable})"
        except Exception:
            return str(self.python_executable)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, PythonEnvironment):
            return other.python_executable == self.python_executable
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.python_executable)


# this is where our own dependencies reside (e.g.: our isolated poetry install)
coveo_stew_environment: Final[PythonEnvironment] = PythonEnvironment(sys.executable)
