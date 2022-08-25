from __future__ import annotations

import os
import textwrap
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Iterable, List

from junit_xml import TestCase, TestSuite, to_xml_report_file

from coveo_stew.ci.runner_status import RunnerStatus

if TYPE_CHECKING:
    from coveo_stew.ci.runner import CIPlan, ContinuousIntegrationRunner


INDENT = " " * 4


def generate_report(name: str, filename: Path, test_cases: Iterable[TestCase]) -> None:
    suite = TestSuite(name, test_cases)
    with filename.open("w", encoding="utf-8") as fd:
        to_xml_report_file(fd, [suite], encoding="utf-8")


def generate_github_step_report(ci_plans: Iterable[CIPlan]) -> None:
    if output_filename := os.getenv("GITHUB_STEP_SUMMARY"):
        markdown = ["# stew ci"]

        for plan in ci_plans:
            markdown.append(f"## **{plan.environment.python_version} :snake:**")

            grouped: Dict[RunnerStatus, List[ContinuousIntegrationRunner]] = defaultdict(list)
            for check in plan.checks:
                grouped[check.status].append(check)

            emoji_map = {
                RunnerStatus.NotRan: ":grey_question:",
                RunnerStatus.Success: ":heavy_check_mark:",
                RunnerStatus.CheckFailed: ":warning:",
                RunnerStatus.Error: ":boom:",
            }

            for status, emoji in emoji_map.items():
                failure = status in (RunnerStatus.Error, RunnerStatus.CheckFailed)
                status_line = ""
                for check in grouped.get(status, []):
                    # the reference leads to the footnote e.g.: [^mypy]
                    reference = f"[^{check.name}]" if failure else ""
                    status_line += f"{check.name} {reference}, "
                if status_line:
                    markdown.append(f"- {emoji} {status_line[:-2]}")

            # we add these as footnotes
            for status, comment in (
                (RunnerStatus.CheckFailed, ""),
                (RunnerStatus.Error, " crashed"),
            ):
                for failed_check in grouped.get(status, []):
                    # footnotes e.g.: [^mypy]:
                    markdown.append(
                        f"[^{failed_check.name}]: **{failed_check.name}{comment}:**\n{INDENT}"
                    )
                    markdown.append(textwrap.indent(failed_check.last_output(), INDENT))
                    if failed_check.last_exception:
                        markdown.append(
                            textwrap.indent(
                                failed_check.last_exception.format(summary=True), INDENT
                            )
                        )

        with Path(output_filename).open("a") as fd:
            fd.write("\n".join(markdown))
