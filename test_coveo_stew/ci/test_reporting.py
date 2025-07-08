from pathlib import Path
from typing import Optional
from unittest.mock import patch

import pytest
from junit_xml import TestCase

from coveo_stew.ci.checks.lib.status import CheckStatus
from coveo_stew.ci.orchestration.results import CheckResults
from coveo_stew.ci.reporting.reporting import (
    _generate_github_step_report,
    generate_github_step_report,
    generate_report,
)


def test_no_failures_returns_only_success_summary() -> None:
    results = [
        CheckResults(
            name="mypy",
            status=CheckStatus.Success,
            exit_code=0,
        ),
        CheckResults(
            name="pytest",
            status=CheckStatus.Success,
            exit_code=0,
        ),
    ]

    report = _generate_github_step_report(results)

    assert "# stew ci" in report
    assert any(
        "mypy" in line and "pytest" in line and ":heavy_check_mark:" in line for line in report
    )


def test_empty_results_returns_minimal_report() -> None:
    report = _generate_github_step_report([])

    assert len(report) == 1
    assert report[0] == "# stew ci"


def test_mixed_results_groups_by_status() -> None:
    results = [
        CheckResults(
            name="mypy",
            status=CheckStatus.Success,
            exit_code=0,
        ),
        CheckResults(
            name="pytest",
            status=CheckStatus.Error,
            exit_code=1,
            output=["Test output"],
            exception=ValueError("Boom"),
        ),
        CheckResults(
            name="black",
            status=CheckStatus.CheckFailed,
            exit_code=1,
            output=["Format error"],
        ),
        CheckResults(
            name="isort",
            status=CheckStatus.NotRan,
            exit_code=1,
        ),
    ]

    report = _generate_github_step_report(results)

    # Check status summary
    assert any(":grey_question: isort" in line for line in report)
    assert any(":heavy_check_mark: mypy" in line for line in report)
    assert any(":warning: black" in line for line in report)
    assert any(":boom: pytest" in line for line in report)

    # Check error details
    error_output = "\n".join(report)
    assert "**black:**" in error_output
    assert "Format error" in error_output
    assert "**pytest crashed:**" in error_output
    assert "Test output" in error_output
    assert "ValueError: Boom" in error_output


def test_failure_includes_output_and_exception() -> None:
    results = [
        CheckResults(
            name="pytest",
            status=CheckStatus.Error,
            exit_code=1,
            output=["Test output"],
            exception=ValueError("Error message"),
        ),
    ]

    report = _generate_github_step_report(results)
    report_text = "\n".join(report)

    assert "**pytest crashed:**" in report_text
    assert "Test output" in report_text
    assert "ValueError: Error message" in report_text


def test_failure_includes_full_exception_details() -> None:
    try:

        def failing_function() -> None:
            raise ValueError("Error message")

        failing_function()
    except ValueError as e:
        error = e

    results = [
        CheckResults(
            name="pytest",
            status=CheckStatus.Error,
            exit_code=0,
            exception=error,
        ),
    ]

    report = _generate_github_step_report(results)
    report_text = "\n".join(report)

    assert "Traceback (most recent call last):" in report_text
    assert "ValueError: Error message" in report_text
    assert "failing_function()" in report_text  # Stack trace should include the function name


def test_junit_report_creates_xml_file(tmp_path: Path) -> None:
    test_case = TestCase("test1", "TestClass1", 1.2)
    test_case2 = TestCase("test2", "TestClass1", 0.5)
    output_file = tmp_path / "junit.xml"

    generate_report("test_suite", output_file, [test_case, test_case2])

    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert "test_suite" in content
    assert "test1" in content
    assert "test2" in content


def test_junit_report_with_failures_includes_error_details(tmp_path: Path) -> None:
    test_case = TestCase("failed_test", "TestClass1", 1.2)
    test_case.add_error_info("Error message", "Error traceback")
    output_file = tmp_path / "junit_error.xml"

    generate_report("error_suite", output_file, [test_case])

    content = output_file.read_text(encoding="utf-8")
    assert "Error message" in content
    assert "Error traceback" in content


@pytest.mark.parametrize("env_var", [None, "summary.md"])
def test_github_step_report_respects_environment_variable(
    env_var: Optional[str], tmp_path: Path
) -> None:
    results = [
        CheckResults(
            name="test",
            status=CheckStatus.Success,
            exit_code=0,
        )
    ]
    summary_file = tmp_path / "summary.md" if env_var else None

    with patch.dict(
        "os.environ", {"GITHUB_STEP_SUMMARY": str(summary_file)} if env_var else {}, clear=True
    ):
        generate_github_step_report(results)

        if env_var:
            assert summary_file.exists()
            content = summary_file.read_text()
            assert "# stew ci" in content
            assert "- :heavy_check_mark: test" in content
        else:
            assert not any(p.name == "summary.md" for p in tmp_path.iterdir())
