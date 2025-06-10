from typing import Any, Dict, List

import pytest

from coveo_stew.ci.stew_ci import _filter_checks


class MockRunner:
    def __init__(self, name: str):
        self.name = name

    def __str__(self) -> str:
        return self.name


@pytest.fixture
def sample_runners() -> List[MockRunner]:
    return [
        MockRunner("black"),
        MockRunner("mypy"),
        MockRunner("pytest"),
        MockRunner("poetry-check"),
    ]


@pytest.mark.parametrize(
    "test_case",
    [
        pytest.param(
            {
                "checks": None,
                "skips": None,
                "expected": ["black", "mypy", "pytest", "poetry-check"],
            },
            id="no_filters",
        ),
        pytest.param(
            {"checks": ["black", "mypy"], "skips": None, "expected": ["black", "mypy"]},
            id="with_checks",
        ),
        pytest.param(
            {"checks": None, "skips": ["pytest", "poetry-check"], "expected": ["black", "mypy"]},
            id="with_skips",
        ),
        pytest.param(
            {"checks": ["BLACK", "MYPY"], "skips": None, "expected": ["black", "mypy"]},
            id="case_insensitive",
        ),
        pytest.param(
            {
                "checks": ["black", "mypy", "pytest"],
                "skips": ["mypy"],
                "expected": ["black", "pytest"],
            },
            id="checks_and_skips",
        ),
        pytest.param({"checks": ["nonexistent"], "skips": None, "expected": []}, id="no_matches"),
    ],
)
def test_filter_runners(sample_runners: List[MockRunner], test_case: Dict[str, Any]) -> None:
    """Parameterized test covering various filter combinations."""
    filtered = list(
        _filter_checks(
            sample_runners,
            include_checks=test_case["checks"],
            skip_checks=test_case["skips"],
            name_getter=lambda r: r.name,
        )
    )
    assert [r.name for r in filtered] == test_case["expected"]


def test_filter_runners_with_custom_name_getter() -> None:
    """Test that the name_getter function works correctly with simple strings."""
    runners: List[str] = ["runner1", "runner2", "runner3"]
    filtered = list(_filter_checks(runners, include_checks=["runner1", "runner3"], name_getter=str))
    assert filtered == ["runner1", "runner3"]


def test_filter_runners_empty_input() -> None:
    """Test that empty input results in empty output."""
    data: list[str] = []  # for mypy 👀
    filtered: list[str] = list(_filter_checks(data))
    assert len(filtered) == 0
