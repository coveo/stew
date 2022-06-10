from pathlib import Path
from typing import Iterable

from junit_xml import TestCase, TestSuite, to_xml_report_file


def generate_report(name: str, filename: Path, test_cases: Iterable[TestCase]) -> None:
    suite = TestSuite(name, test_cases)
    with filename.open("w", encoding="utf-8") as fd:
        to_xml_report_file(fd, [suite], encoding="utf-8")
