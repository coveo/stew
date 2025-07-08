from __future__ import annotations

import os
import random
import textwrap
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Iterator

from coveo_systools.subprocess import DetailedCalledProcessError
from junit_xml import TestCase, TestSuite, to_xml_report_file

from coveo_stew.ci.checks.lib.status import CheckStatus, check_status_color_map
from coveo_stew.ci.orchestration.results import CheckResults

INDENT = " " * 4


def generate_report(name: str, filename: Path, test_cases: Iterable[TestCase]) -> None:
    """Generates a JUnit XML report file."""
    suite = TestSuite(name, test_cases)
    with filename.open("w", encoding="utf-8") as fd:
        to_xml_report_file(fd, [suite], encoding="utf-8")


def generate_github_step_report(results: Iterable[CheckResults]) -> None:
    """Generates a GitHub Actions step summary report."""
    if not (output_filename := os.getenv("GITHUB_STEP_SUMMARY")):
        return

    step_report = _generate_github_step_report(results)

    with Path(output_filename).open("a") as fd:
        fd.write("\n".join(step_report))


def _generate_github_step_report(results: Iterable[CheckResults]) -> list[str]:
    """Generate a markdown report for GitHub Actions step summary."""
    markdown = ["# stew ci"]

    # Group results by status
    grouped: dict[CheckStatus, list[CheckResults]] = defaultdict(list)
    for result in results:
        grouped[result.status].append(result)

    emoji_map = {
        CheckStatus.NotRan: ":grey_question:",
        CheckStatus.Success: ":heavy_check_mark:",
        CheckStatus.CheckFailed: ":warning:",
        CheckStatus.Error: ":boom:",
    }

    # Print summary section with statuses and emojis
    for status, emoji in emoji_map.items():
        failure = status in (CheckStatus.Error, CheckStatus.CheckFailed)
        status_line = ""
        for result in grouped.get(status, []):
            # the reference leads to the footnote e.g.: [^mypy]
            reference = f"[^{result.name}]" if failure else ""
            status_line += f"{result.name} {reference}, "
        if status_line:
            markdown.append(f"- {emoji} {status_line[:-2]}")

    # Add details as footnotes for failures
    for status, comment in (
        (CheckStatus.CheckFailed, ""),
        (CheckStatus.Error, " crashed"),
    ):
        for failed_result in grouped.get(status, []):
            # footnotes e.g.: [^mypy]:
            markdown.append(
                f"[^{failed_result.name}]: **{failed_result.name}{comment}:**\n{INDENT}"
            )
            if failed_result.output:
                markdown.append(textwrap.indent("\n".join(failed_result.output), INDENT))
            if failed_result.exception:
                exception = failed_result.exception
                if isinstance(exception, DetailedCalledProcessError):
                    markdown.append(textwrap.indent(exception.format(summary=True), INDENT))
                else:
                    from traceback import format_exception

                    exception_details = format_exception(
                        type(exception),
                        exception,
                        exception.__traceback__,
                    )
                    markdown.append(textwrap.indent("".join(exception_details), INDENT))

    return markdown


def _align(text: str, width: int, align: str = "<") -> str:
    """Align text with the given width. The text must only contain printable characters.

    parameters:
        align: < for left align, > for right align
    """
    padding = " " * (width - len(text))
    if align == "<":
        return text + padding
    return padding + text


def _get_column_widths(results: list[CheckResults]) -> tuple[int, int, int, int]:
    """Calculate the width needed for each column, respecting minimum values.

    Returns:
        Tuple of (check_width, status_width, duration_width, col_spacing_width)
    """
    min_check_width = 28  # leaving this airy on purpose
    min_status_width = 7  # Common status is "Success"
    min_duration_width = 8  # length of "Duration" header
    col_spacing = 2

    # Check width is the longest check name
    check_width = max((len(result.name) for result in results), default=min_check_width)
    check_width = max(check_width, min_check_width)

    # Status width is the longest status name
    status_width = max((len(result.status.name) for result in results), default=min_status_width)
    status_width = max(status_width, min_status_width)

    # Duration width is based on the longest duration value
    max_duration = max((result.duration_seconds or 0.0 for result in results), default=0.0)
    # Calculate width needed for the duration: len("Duration"), or formatted duration + "s"
    duration_format = f"{max_duration:.2f}s"
    duration_width = max(len("Duration"), len(duration_format))
    duration_width = max(duration_width, min_duration_width)

    return check_width, status_width, duration_width, col_spacing


def generate_summary_table(results: list[CheckResults]) -> str:
    """Generates a summary table of all checks and their durations."""
    check_width, status_width, duration_width, col_spacing_width = _get_column_widths(results)
    col_spacing = col_spacing_width * " "

    lines: list[str] = [""]  # start with an empty line

    # Print header row
    header_check = _align("Check", check_width)
    header_status = _align("Status", status_width)
    header_duration = "Duration".rjust(duration_width)
    lines.append(f"{header_check}{col_spacing}{header_status}{col_spacing}{header_duration}")

    # Create separator line with consistent spacing
    separator_check = "-" * check_width
    separator_status = "-" * status_width
    separator_duration = "-" * duration_width
    lines.append(
        f"{separator_check}{col_spacing}{separator_status}{col_spacing}{separator_duration}"
    )

    for result in results:
        # First align the plain text
        name_col = _align(result.name, check_width)
        status_col = _align(result.status.name, status_width)

        # Use color mapping from the CheckStatus enum for consistency
        status_col = f"<fg={check_status_color_map[result.status]}>{status_col}</>"

        duration = result.duration_seconds or 0.0
        # Right-align the duration
        duration_str = f"{duration:.2f}s".rjust(duration_width)

        lines.append(f"{name_col}{col_spacing}{status_col}{col_spacing}{duration_str}")

    return "\n".join(lines)


CHECK_FAILED_MESSAGES = [
    # Standard messages
    "reported",
    "found something",
    "found stuff",
    "is saying",
    "says",
    "has issues",
    "has feedback",
    "output",
    "result",
    # Attention-focused
    "wants your attention",
    "needs your help",
    "needs review",
    "requires attention",
    # Technical observations
    "flagged issues",
    "raised concerns",
    "detected anomalies",
    "highlighted problems",
    "spotted trouble",
    "signaled warnings",
    "triggered alerts",
    "has suggestions",
    # Gentle hints
    "flagged something odd",
    "thinks something's off",
    "wants a second look",
    "raised a red flag",
    "needs another pair of eyes",
    "would like your input",
    # Professional disagreement
    "isn't happy",
    "has a complaint",
    "is not satisfied",
    "isn't convinced",
    "has concerns",
    "disagrees",
    "requests changes",
    # Light-hearted but professional
    "has a bone to pick",
    "would like a word",
    "needs a helping hand",
    "is waving a yellow flag",
    "tapped you on the shoulder",
    "would like your expertise",
    "suggests improvements",
    # Constructive feedback
    "offers suggestions",
    "spotted room for improvement",
    "sees an opportunity",
    "found potential issues",
    "identified concerns",
    "noticed something",
    # Collaborative tone
    "invites discussion",
    "seeks clarification",
    "requests your insights",
    "could use your wisdom",
    "welcomes your review",
    "would appreciate your thoughts",
]


# Generator yielding each failed check message once per cycle, shuffled
def _check_failed_message_generator() -> Iterator[str]:
    messages = CHECK_FAILED_MESSAGES.copy()
    random.shuffle(messages)
    while True:
        for msg in messages:
            yield msg
        random.shuffle(messages)


# module-level generator instance
random_check_failed_message = _check_failed_message_generator()


def generate_check_result(check_result: CheckResults) -> str:
    lines = []
    prefix = f"<fg=light_blue>{check_result.name}</fg>"
    emoji = check_result.status.emoji()

    if check_result.status == CheckStatus.NotRan:
        lines.append(f" {emoji} <fg=yellow>{prefix} didn't run.</>")

    elif check_result.status == CheckStatus.Success:
        pass  # the summary table is enough for this

    elif check_result.status == CheckStatus.CheckFailed:
        suffix = next(random_check_failed_message)
        lines.append("<fg=magenta>---</>")
        lines.append(f" {emoji} <fg=magenta>{prefix} {suffix}:</>")
        lines.append("")

        if check_result.output:
            lines.append(check_result.get_output_string())

    elif check_result.status == CheckStatus.Error:
        lines.append("<fg=red>---</>")
        lines.append(f" {emoji} <fg=red>{prefix} exited unexpectedly!!</> 😱")

        if exception := check_result.exception:
            if isinstance(exception, DetailedCalledProcessError):
                exception_text = "\n".join(format_detailed_called_process_error_output(exception))
            else:
                exception_text = str(exception)

            lines.append(exception_text.strip())
        else:
            lines.append(" 🤭 Oops, the test failed, but there wasn't any exception.")

    return "\n".join(lines)


def format_detailed_called_process_error_output(
    exception: DetailedCalledProcessError, is_error_or_verbose: bool = True
) -> list[str]:
    """
    Format command output with color-coded indicators for stdout/stderr.
    `is_error` is used to distinguish between a failed check (clean output) and an error (detailed output).
    Failed checks will also display the full information on verbose mode.
    """
    output = []

    if is_error_or_verbose:
        output.append(f"command: {exception.command_str()}")
        output.append(f"exit code: {exception.returncode}")

    if exception.stdout:
        if is_error_or_verbose:
            output.append("<fg=yellow>")
        output.append(exception.decode_stdout().strip() + ("</>" if is_error_or_verbose else ""))

    if exception.stderr:
        output.append("<fg=red>")
        output.append(exception.decode_stderr().strip() + "</>")

    return output
