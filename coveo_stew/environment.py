import platform
from enum import Enum
from functools import lru_cache
from pathlib import Path
from subprocess import PIPE, CalledProcessError
from typing import Any, List, Optional, Tuple, Union

from coveo_styles.styles import ExitWithFailure
from coveo_systools.filesystem import find_application
from coveo_systools.subprocess import check_output

from coveo_stew.exceptions import ToolNotFound

RUNNING_IN_WINDOWS: bool = bool(platform.system() == "Windows")


class PythonTool(Enum):
    Python = "python"
    Poetry = "poetry"
    Mypy = "mypy"
    Pytest = "pytest"
    Pip = "pip"
    Black = "black"

    def __str__(self) -> str:
        return self.value


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
            raise ExitWithFailure(
                suggestions="Launch `poetry env use /path/to/python`"
            ) from FileNotFoundError(f"Cannot find a python executable in {environment_path}")

        self.python_executable: Path = python_path

    def build_command(self, tool: Union[PythonTool, str], *args: Any) -> List[Any]:
        """
        Builds a command for a python tool. If the tool cannot be found in the environment,
        it will try to find one from the PATH.
        """
        return [*find_python_tool(tool, environment=self), *args]

    @lru_cache
    def has_tool(self, tool: Union[PythonTool, str]) -> bool:
        try:
            _ = check_output(self.python_executable, "-c", f"import {tool};", stderr=PIPE)
            return True
        except CalledProcessError:
            return False

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


def find_python_tool(
    tool: Union[PythonTool, str], *, environment: Optional[PythonEnvironment] = None
) -> Tuple[Union[str, Path], ...]:
    """
    Finds a tool and returns the arguments to call it from the command line.

    For instance, if `black` is found in `environment`:
        "/path/to/env/python.exe", "-m", "black"

    If it was found from the system:
        "/path/to/black"
    """
    if environment and environment.has_tool(tool):
        return environment.python_executable, "-m", str(tool)

    if app := find_application(str(tool)):
        return (app,)

    raise ToolNotFound(
        f"""
{tool} was not found, or could not be imported.

Starting from coveo-stew 3.0.0, 3rd party tools are no longer provided:

- You can add {tool} to your `pyproject.toml`, typically in the `[tool.poetry.dev-dependencies]` section.
- Or you can install {tool} to your system so that it can be found in the PATH
"""
    )
