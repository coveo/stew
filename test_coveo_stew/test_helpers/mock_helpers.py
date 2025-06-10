"""Helper functions and classes for mocking in tests."""

from typing import Any, Dict, List, cast
from unittest.mock import MagicMock, PropertyMock, create_autospec

from coveo_stew.ci.checks.lib.base_check import BaseCheck
from coveo_stew.environment import PythonEnvironment


class MockFactory:
    @staticmethod
    def _create_mock(cls: Any) -> MagicMock:
        return cast(MagicMock, create_autospec(cls, instance=True, spec_set=True))

    @staticmethod
    def create_runner(name: str, supports_autofix: bool = False) -> MagicMock:
        runner = MockFactory._create_mock(BaseCheck)

        # Configure name property
        name_mock = PropertyMock(return_value=name)
        type(runner).name = name_mock

        # Configure supports_auto_fix property
        supports_mock = PropertyMock(return_value=supports_autofix)
        type(runner).supports_auto_fix = supports_mock

        # # Create an AsyncMock for launch method
        # launch_mock = AsyncMock()
        # launch_mock.return_value = RunnerResult(
        #     status=RunnerStatus.Success, name="hey", environment=MockFactory.create_environment()
        # )
        # setattr(runner, "launch", launch_mock)

        return runner

    @staticmethod
    def create_runners(configs: List[Dict[str, Any]]) -> List[MagicMock]:
        return [
            MockFactory.create_runner(
                name=config["name"], supports_autofix=config["supports_auto_fix"]
            )
            for config in configs
        ]

    @staticmethod
    def create_environment(python_version: str = "3.9") -> MagicMock:
        env = MockFactory._create_mock(PythonEnvironment)
        python_version_mock = PropertyMock(return_value=python_version)
        type(env).python_version = python_version_mock
        return env

    @staticmethod
    def create_environments(count: int, python_version: str = "3.9") -> List[MagicMock]:
        return [MockFactory.create_environment(python_version) for _ in range(count)]
