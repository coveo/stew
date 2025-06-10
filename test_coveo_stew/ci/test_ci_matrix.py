import time
from collections import defaultdict
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from coveo_stew.ci.orchestration.matrix import CIMatrix, CIMatrixWorkflowOptions
from coveo_stew.ci.orchestration.task import Task
from coveo_stew.environment import PythonEnvironment
from test_coveo_stew.test_helpers.mock_helpers import MockFactory


def create_runner_mocks(runners_config: List[Dict[str, Any]]) -> List[MagicMock]:
    """Create runner mocks based on configuration."""
    return MockFactory.create_runners(runners_config)


def create_one_runner_batch_mock(
    name: str = "normal-runner",
    supports_autofix: bool = False,
) -> List[MagicMock]:
    return create_runner_mocks(
        [
            {
                "name": name,
                "supports_auto_fix": supports_autofix,
            }
        ]
    )


def test_empty_environments_raises_error() -> None:
    """Matrix creation should fail when no environments are provided."""
    with pytest.raises(ValueError, match="At least one environment is required"):
        CIMatrix(environments=[], checks=[MagicMock()])


def test_empty_runners_raises_error() -> None:
    """Matrix creation should fail when no runners are provided."""
    with pytest.raises(ValueError, match="At least one check is required"):
        CIMatrix(environments=[MagicMock()], checks=[])


class CIMatrixTestCase:
    """Test case configuration for CIMatrix tests."""

    def __init__(
        self,
        name: str,
        runners_config: List[Dict[str, Any]],
        env_count: int,
        workflow: CIMatrixWorkflowOptions,
        expected_autofix: List[str],
        expected_checks: List[str],
    ):
        """
        Configure a test case for CIMatrix.

        Args:
            name: Test case name/description
            runners_config: List of runner configurations with keys:
                - supports_auto_fix: bool
                - name: str
            env_count: Number of environments to create
            workflow: The workflow mode to pass to next_batch
            expected_autofix: List of runner names expected to run in autofix mode
            expected_checks: List of runner names expected to run in check mode
        """
        self.name = name
        self.runners_config = runners_config
        self.env_count = env_count
        self.workflow = workflow
        self.expected_autofix = expected_autofix
        self.expected_checks = expected_checks

    def create_runners(self) -> List[MagicMock]:
        return create_runner_mocks(self.runners_config)

    def create_environments(self) -> List[MagicMock]:
        """Create environment mocks based on configuration."""
        return MockFactory.create_environments(self.env_count)

    def get_batches(self) -> List[List[Task]]:
        """Get the batches from a matrix created with this test case's configuration."""
        matrix = CIMatrix(environments=self.create_environments(), checks=self.create_runners())
        return [
            list(batch) for batch in matrix.generate_task_batches(workflow_options=self.workflow)
        ]

    def split_tasks(self, batches: List[List[Task]]) -> tuple[List[Task], List[Task]]:
        """Split tasks into autofix and check tasks."""
        autofix_tasks = []
        check_tasks = []
        for batch in batches:
            for task in batch:
                if task.enable_autofix:
                    autofix_tasks.append(task)
                else:
                    check_tasks.append(task)
        return autofix_tasks, check_tasks

    def get_autofix_tasks(self, batches: List[List[Task]]) -> List[Task]:
        """Get all autofix tasks from the batches."""
        return self.split_tasks(batches)[0]

    def get_check_tasks(self, batches: List[List[Task]]) -> List[Task]:
        """Get all check tasks from the batches."""
        return self.split_tasks(batches)[1]


def get_runner_names(tasks: List[Task]) -> List[str]:
    """Get sorted list of unique runner names from tasks."""
    return sorted(set(task.check.name for task in tasks))


@pytest.mark.parametrize(
    "test_case",
    [
        CIMatrixTestCase(
            name="Single runner with autofix enabled",
            runners_config=[{"supports_auto_fix": True, "name": "black"}],
            env_count=1,
            workflow=CIMatrixWorkflowOptions.CHECK | CIMatrixWorkflowOptions.AUTOFIX,
            expected_autofix=["black"],
            expected_checks=["black"],
        ),
        CIMatrixTestCase(
            name="Single runner with autofix disabled",
            runners_config=[{"supports_auto_fix": True, "name": "black"}],
            env_count=1,
            workflow=CIMatrixWorkflowOptions.CHECK,
            expected_autofix=[],
            expected_checks=["black"],
        ),
        CIMatrixTestCase(
            name="Multiple runners with mixed autofix support",
            runners_config=[
                {"supports_auto_fix": True, "name": "black"},
                {"supports_auto_fix": False, "name": "mypy"},
                {"supports_auto_fix": True, "name": "isort"},
            ],
            env_count=2,
            workflow=CIMatrixWorkflowOptions.CHECK | CIMatrixWorkflowOptions.AUTOFIX,
            expected_autofix=["black", "isort"],
            expected_checks=["black", "isort", "mypy"],
        ),
        CIMatrixTestCase(
            name="Multiple environments with multiple runners",
            runners_config=[
                {"supports_auto_fix": True, "name": "black"},
                {"supports_auto_fix": False, "name": "mypy"},
            ],
            env_count=3,
            workflow=CIMatrixWorkflowOptions.CHECK,
            expected_autofix=[],
            expected_checks=["black", "mypy"],
        ),
        CIMatrixTestCase(
            name="Two autofix and two check runners",
            runners_config=[
                {"supports_auto_fix": True, "name": "black"},
                {"supports_auto_fix": False, "name": "mypy"},
                {"supports_auto_fix": True, "name": "isort"},
                {"supports_auto_fix": False, "name": "pytest"},
            ],
            env_count=2,
            workflow=CIMatrixWorkflowOptions.CHECK | CIMatrixWorkflowOptions.AUTOFIX,
            expected_autofix=["black", "isort"],
            expected_checks=["black", "isort", "mypy", "pytest"],
        ),
        CIMatrixTestCase(
            name="No autofix runners but autofix enabled",
            runners_config=[
                {"supports_auto_fix": False, "name": "mypy"},
                {"supports_auto_fix": False, "name": "pytest"},
            ],
            env_count=2,
            workflow=CIMatrixWorkflowOptions.CHECK | CIMatrixWorkflowOptions.AUTOFIX,
            expected_autofix=[],  # No autofix tasks even though autofix flag is set
            expected_checks=["mypy", "pytest"],  # All runners should run as checks
        ),
        CIMatrixTestCase(
            name="Single environment with multiple runners",
            runners_config=[
                {"supports_auto_fix": True, "name": "black"},
                {"supports_auto_fix": True, "name": "isort"},
                {"supports_auto_fix": False, "name": "mypy"},
            ],
            env_count=1,
            workflow=CIMatrixWorkflowOptions.CHECK | CIMatrixWorkflowOptions.AUTOFIX,
            expected_autofix=["black", "isort"],
            expected_checks=["black", "isort", "mypy"],
        ),
        CIMatrixTestCase(
            name="Autofix only without checks",
            runners_config=[
                {"supports_auto_fix": True, "name": "black"},
                {"supports_auto_fix": True, "name": "isort"},
                {"supports_auto_fix": False, "name": "mypy"},
            ],
            env_count=2,
            workflow=CIMatrixWorkflowOptions.AUTOFIX,
            expected_autofix=["black", "isort"],
            expected_checks=[],  # No check tasks should run
        ),
    ],
    ids=lambda test_case: test_case.name,
)
class TestCIMatrix:
    def test_autofix_tasks_use_single_environment(self, test_case: CIMatrixTestCase) -> None:
        """All autofix tasks should use the same environment."""
        if not test_case.expected_autofix:
            pytest.skip("Cannot validate; no expected autofix runners")

        batches = test_case.get_batches()
        autofix_tasks = test_case.get_autofix_tasks(batches)

        assert len(autofix_tasks) > 0, "Expected at least one autofix task"
        autofix_envs = {task.environment for task in autofix_tasks}
        assert len(autofix_envs) == 1, "Autofix tasks should use exactly one environment"

    def test_autofix_tasks_are_in_separate_batches(self, test_case: CIMatrixTestCase) -> None:
        """Each autofix task should be in its own batch at the start."""
        if not test_case.expected_autofix:
            pytest.skip("Cannot validate; no expected autofix runners")

        batches = test_case.get_batches()
        autofix_count = len(test_case.expected_autofix)

        # Check first N batches where N is number of expected autofix tasks
        for i in range(autofix_count):
            tasks = batches[i]
            assert len(tasks) == 1, f"Expected autofix batch {i} to have exactly one task"
            task = tasks[0]
            assert task.enable_autofix, f"Task in batch {i} should have autofix enabled"
            assert task.purpose == "autofix", f"Task in batch {i} should have purpose 'autofix'"
            assert task.check.name in test_case.expected_autofix

        # Verify that remaining batches don't contain any autofix tasks
        if len(batches) > autofix_count:
            for i in range(autofix_count, len(batches)):
                for task in batches[i]:
                    assert (
                        not task.enable_autofix
                    ), f"Task in non-autofix batch {i} should not have autofix enabled"
                    assert (
                        task.purpose != "autofix"
                    ), f"Task in batch {i} should not have purpose 'autofix'"

    def test_expected_autofix_runners_are_present(self, test_case: CIMatrixTestCase) -> None:
        """All expected autofix runners should be present in autofix tasks."""
        batches = test_case.get_batches()
        autofix_tasks = test_case.get_autofix_tasks(batches)

        autofix_runner_names = get_runner_names(autofix_tasks)
        assert autofix_runner_names == sorted(
            test_case.expected_autofix
        ), f"Expected autofix runners {sorted(test_case.expected_autofix)}, got {autofix_runner_names}"

    def test_check_tasks_run_in_all_environments(self, test_case: CIMatrixTestCase) -> None:
        """Each check task should run once in each environment."""
        batches = test_case.get_batches()
        check_tasks = test_case.get_check_tasks(batches)

        # Group check tasks by runner
        runners_to_envs: Dict[str, set[PythonEnvironment]] = defaultdict(set)
        for task in check_tasks:
            runners_to_envs[task.check.name].add(task.environment)

        # Each runner should have run in each environment exactly once
        for runner_name, runner_envs in runners_to_envs.items():
            assert (
                len(runner_envs) == test_case.env_count
            ), f"Runner {runner_name} should run in {test_case.env_count} environments, but ran in {len(runner_envs)}"

    def test_expected_check_runners_are_present(self, test_case: CIMatrixTestCase) -> None:
        """All expected check runners should be present."""
        batches = test_case.get_batches()
        check_tasks = test_case.get_check_tasks(batches)

        check_runner_names = get_runner_names(check_tasks)
        assert check_runner_names == sorted(
            test_case.expected_checks
        ), f"Expected check runners {sorted(test_case.expected_checks)}, got {check_runner_names}"

    def test_correct_number_of_check_tasks(self, test_case: CIMatrixTestCase) -> None:
        """Should have exactly one check task per runner per environment."""
        batches = test_case.get_batches()
        check_tasks = test_case.get_check_tasks(batches)

        expected_check_task_count = len(test_case.expected_checks) * test_case.env_count
        assert (
            len(check_tasks) == expected_check_task_count
        ), f"Expected {expected_check_task_count} check tasks ({len(test_case.expected_checks)} runners * {test_case.env_count} envs), got {len(check_tasks)}"

    def test_autofix_tasks_come_before_check_tasks(self, test_case: CIMatrixTestCase) -> None:
        """All autofix tasks should come before any check tasks in the batch sequence."""
        if not test_case.expected_autofix or not test_case.expected_checks:
            pytest.skip("Cannot validate; need both autofix and check tasks")

        batches = test_case.get_batches()

        # Find the first batch that contains check tasks
        first_check_batch_index = None
        for i, batch in enumerate(batches):
            if any(not task.enable_autofix for task in batch):
                first_check_batch_index = i
                break

        assert first_check_batch_index is not None, "No check tasks found in batches"

        # Ensure no autofix tasks appear in or after the first check batch
        for i in range(first_check_batch_index, len(batches)):
            for task in batches[i]:
                assert (
                    not task.enable_autofix
                ), f"Autofix task found in batch {i}, after check tasks started"

    def test_each_autofix_runner_appears_exactly_once(self, test_case: CIMatrixTestCase) -> None:
        """Each runner that supports autofix should appear exactly once in autofix tasks when autofix is enabled."""
        if not test_case.expected_autofix:
            pytest.skip("Cannot validate; no expected autofix runners")

        batches = test_case.get_batches()
        autofix_tasks = test_case.get_autofix_tasks(batches)

        # Count occurrences of each runner in autofix tasks
        runner_counts: dict[str, int] = {}
        for task in autofix_tasks:
            runner_name = task.check.name
            runner_counts[runner_name] = runner_counts.get(runner_name, 0) + 1

        # Each runner should appear exactly once
        for runner_name in test_case.expected_autofix:
            assert (
                runner_counts.get(runner_name) == 1
            ), f"Expected runner {runner_name} to appear exactly once in autofix tasks, but got {runner_counts.get(runner_name, 0)}"

        # No unexpected runners should appear
        for runner_name in runner_counts:
            assert (
                runner_name in test_case.expected_autofix
            ), f"Unexpected runner {runner_name} found in autofix tasks"

    def test_check_tasks_are_balanced_across_batches(self, test_case: CIMatrixTestCase) -> None:
        """Check tasks should be balanced across batches with a consistent distribution pattern."""
        if not test_case.expected_checks or test_case.env_count <= 1:
            pytest.skip("Cannot validate; need check tasks and multiple environments")

        batches = test_case.get_batches()

        # Skip autofix batches
        autofix_count = len(test_case.expected_autofix)
        check_batches = batches[autofix_count:]

        if not check_batches:
            pytest.skip("No check batches found")

        # For each batch, track which runners are used
        for i, batch in enumerate(check_batches):
            if not batch:  # Skip empty batches
                continue

            # Each runner should appear at most once per environment in a batch
            runner_env_pairs = {(task.check.name, task.environment) for task in batch}
            assert len(runner_env_pairs) == len(
                batch
            ), f"Batch {i + autofix_count} has duplicate runner-environment pairs"

            # Group tasks by runner in the batch
            runners_in_batch: dict[str, list[Task]] = {}
            for task in batch:
                runner_name = task.check.name
                if runner_name not in runners_in_batch:
                    runners_in_batch[runner_name] = []
                runners_in_batch[runner_name].append(task)

            # Each runner should use different environments within a batch
            for runner_name, tasks in runners_in_batch.items():
                envs = {task.environment for task in tasks}
                assert len(envs) == len(
                    tasks
                ), f"Runner {runner_name} in batch {i + autofix_count} is using the same environment multiple times"


class TestTask:
    def setup_method(self) -> None:
        """Setup common test fixtures."""
        self.runner = create_one_runner_batch_mock()[0]
        self.env = MockFactory.create_environment()

    def test_task_initial_state(self) -> None:
        """Test initial state of a newly created task."""
        task = Task(check=self.runner, environment=self.env, enable_autofix=False)
        assert not task.is_in_progress
        assert not task.is_complete
        assert task.duration == 0.0
        assert task.purpose == "check"  # default value

    def test_task_in_progress(self) -> None:
        """Test task state when in progress."""
        task = Task(check=self.runner, environment=self.env, enable_autofix=False)
        task.started_at = time.time()
        time.sleep(0.001)  # Ensure we get a non-zero duration
        assert task.is_in_progress
        assert not task.is_complete
        assert task.duration > 0.0

    def test_task_completed(self) -> None:
        """Test task state when completed."""
        task = Task(check=self.runner, environment=self.env, enable_autofix=False)
        task.started_at = time.time() - 1  # Started 1 second ago
        task.ended_at = time.time()
        assert not task.is_in_progress
        assert task.is_complete
        assert 0.9 < task.duration < 1.1  # Should be approximately 1 second

    def test_task_duration_not_started(self) -> None:
        """Test duration when task hasn't started."""
        task = Task(check=self.runner, environment=self.env, enable_autofix=False)
        assert task.duration == 0.0

    def test_task_with_custom_purpose(self) -> None:
        """Test task creation with custom purpose."""
        task = Task(check=self.runner, environment=self.env, enable_autofix=True, purpose="autofix")
        assert task.purpose == "autofix"
        assert task.enable_autofix


def test_matrix_requires_at_least_one_flag() -> None:
    """Verify that next_batch raises ValueError when no flags are set."""
    runners = create_one_runner_batch_mock()
    env_mock = MockFactory.create_environment()
    matrix = CIMatrix(environments=[env_mock], checks=runners)

    with pytest.raises(ValueError, match="At least one workflow flag must be set"):
        # Converting to list to force generator evaluation
        list(matrix.generate_task_batches(workflow_options=CIMatrixWorkflowOptions.NONE))
