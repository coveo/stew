import sys
from pathlib import Path
from typing import cast
from unittest import mock

import pytest
from coveo_ref import ref
from coveo_systools.subprocess import check_output
from coveo_testing.parametrize import parametrize
from packaging.version import Version

from coveo_stew.context import context
from coveo_stew.environment import (
    PythonEnvironment,
    PythonTool,
    ToolNotFound,
    _find_poetry_version,
    find_python_tool,
)


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


@pytest.fixture
def mock_environment() -> PythonEnvironment:
    env = mock.Mock(spec=PythonEnvironment)
    env.python_executable = Path("/path/to/python.exe")
    return env


def test_find_python_tool_stew_as_poetry_plugin(mock_environment: PythonEnvironment) -> None:
    with (
        mock.patch.object(context, "is_running_as_poetry_plugin", True),
        mock.patch.object(sys, "executable", "/path/to/poetry"),
    ):
        result = find_python_tool(PythonTool.Stew, environment=mock_environment)
        assert result == ("/path/to/poetry", "-m", "poetry", "stew")


def test_find_python_tool_in_environment(mock_environment: PythonEnvironment) -> None:
    mock_has_tool = cast(mock.MagicMock, mock_environment.has_tool)
    mock_has_tool.return_value = True
    result = find_python_tool("black", environment=mock_environment)
    assert result == (mock_environment.python_executable, "-m", "black")
    mock_has_tool.assert_called_once_with("black")


def test_find_python_tool_stew_in_environment(mock_environment: PythonEnvironment) -> None:
    mock_has_tool = cast(mock.MagicMock, mock_environment.has_tool)
    mock_has_tool.return_value = True
    result = find_python_tool(PythonTool.Stew, environment=mock_environment)
    assert result == (mock_environment.python_executable, "-m", "coveo_stew")
    mock_has_tool.assert_called_once_with("coveo_stew")


@mock.patch("coveo_stew.environment.find_application")
def test_find_python_tool_in_system_path(
    mock_find_application: mock.MagicMock, mock_environment: PythonEnvironment
) -> None:
    mock_has_tool = cast(mock.MagicMock, mock_environment.has_tool)
    mock_has_tool.return_value = False
    mock_find_application.return_value = "/usr/local/bin/black"
    result = find_python_tool("black", environment=mock_environment)
    assert result == ("/usr/local/bin/black",)
    mock_find_application.assert_called_once_with("black")


@mock.patch("coveo_stew.environment.find_application")
def test_find_python_tool_not_found(
    mock_find_application: mock.MagicMock, mock_environment: PythonEnvironment
) -> None:
    mock_has_tool = cast(mock.MagicMock, mock_environment.has_tool)
    mock_has_tool.return_value = False
    mock_find_application.return_value = None
    with pytest.raises(ToolNotFound):
        find_python_tool("nonexistent", environment=mock_environment)


def test_find_python_tool_no_environment() -> None:
    with mock.patch("coveo_stew.environment.find_application") as mock_find_application:
        mock_find_application.return_value = "/usr/local/bin/black"
        result = find_python_tool("black")
        assert result == ("/usr/local/bin/black",)
