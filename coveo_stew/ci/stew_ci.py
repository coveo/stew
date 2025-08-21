import asyncio
from typing import Callable, Iterable, Iterator, Optional

from cleo.io.io import IO

from coveo_stew.ci.checks.lib.status import CheckStatus
from coveo_stew.ci.orchestration.matrix import CIMatrixWorkflowOptions
from coveo_stew.ci.orchestration.orchestrator import CIOrchestrator, T
from coveo_stew.ci.orchestration.results import CheckResults
from coveo_stew.ci.reporting.reporting import (
    generate_check_result,
    generate_github_step_report,
    generate_summary_table,
)
from coveo_stew.stew import PythonProject


def stew_ci(
    io: IO,
    pyproject: PythonProject,
    *,
    auto_fix: bool = False,
    checks: Optional[Iterable[str]] = None,
    skips: Optional[Iterable[str]] = None,
    quick: bool = False,
    parallel: bool = True,
    github: bool = False,
    raise_exceptions: bool = False,
) -> CheckStatus:
    """Run check tasks with the given checks and configuration.

    Args:
        io: The IO interface for writing output
        pyproject: The python project to run CI on
        auto_fix: Whether to attempt automatic fixes
        checks: Optional list of specific checks to run
        skips: Optional list of checks to skip
        quick: Skip environment setup if True
        parallel: Run checks in parallel if True
        github: Generate GitHub-specific report if True
        raise_exceptions: Tells the orchestrator to raise exceptions instead of logging them
    """
    filtered_checks = list(
        _filter_checks(
            pyproject.ci.checks,
            name_getter=lambda r: r.name,
            include_checks=checks,
            skip_checks=skips,
        )
    )

    # Display checks that will be skipped

    if skipped_names := [
        c.name for c in pyproject.ci.checks if c.name not in {f.name for f in filtered_checks}
    ]:
        io.write_line(f"<fg=light_gray>Skipping checks: {', '.join(skipped_names)}</fg>")

    if not filtered_checks:
        io.write_line(
            f"{pyproject.poetry.package.pretty_name}: <fg=red>No checks configured or all checks skipped.</>"
        )
        return CheckStatus.NotRan

    if not quick:
        for env in pyproject.virtual_environments(create_default_if_missing=True):
            pyproject.install(environment=env, sync=True)

    workflow_options = CIMatrixWorkflowOptions.CHECK
    if auto_fix:
        workflow_options |= CIMatrixWorkflowOptions.AUTOFIX
    if not parallel:
        workflow_options |= CIMatrixWorkflowOptions.SEQUENTIAL

    orchestrator = CIOrchestrator(
        environments=list(pyproject.virtual_environments()),
        checks=filtered_checks,
        workflow_options=workflow_options,
        io=io,
        raise_exceptions=raise_exceptions,
    )

    try:
        result = asyncio.run(orchestrator.orchestrate())
    except KeyboardInterrupt:
        # Ensure we still get the result even if interrupted
        io.write_line("\n<fg=blue>Preparing results for completed and cancelled checks...</>")

        # Track any remaining checks as cancelled
        # This ensures ALL checks appear in the summary table
        ran_check_names = {result.name for result in orchestrator.results}
        for check in filtered_checks:
            if check.name not in ran_check_names:
                orchestrator.results.append(
                    CheckResults(
                        name=check.name,
                        status=CheckStatus.Cancelled,
                        exception=None,
                        duration_seconds=0.0,
                    )
                )

        result = CheckStatus.Cancelled

    # Display results to the user
    io.write_line("\n")  # this is 2 lines
    for check_result in orchestrator.results:
        output = generate_check_result(check_result)
        if output:
            io.write_line(output)
            io.write_line("\n")  # yup, 2 lines again!

    # Display summary table after individual results
    summary = generate_summary_table(orchestrator.results)
    io.write_line(summary)

    if github:
        generate_github_step_report(orchestrator.results)

    return result


def _filter_checks(
    checks: Iterable[T],
    include_checks: Optional[Iterable[str]] = None,
    skip_checks: Optional[Iterable[str]] = None,
    name_getter: Callable[[T], str] = str,
) -> Iterator[T]:
    """Filter checks based on checks and skips parameters.

    Args:
        checks: The checks to filter
        name_getter: A function that extracts the name from a check, defaults to str() for string inputs
        include_checks: If provided, only include these checks
        skip_checks: If provided, exclude these checks
    """
    include_checks = [check.lower() for check in include_checks] if include_checks else []
    skip_checks = [skip.lower() for skip in skip_checks] if skip_checks else []

    for check in checks:
        name = name_getter(check)
        if (include_checks and name.lower() not in include_checks) or name.lower() in skip_checks:
            continue

        yield check
