from dataclasses import dataclass, field
from typing import List, Optional

from junit_xml import TestCase

from coveo_stew.ci.checks.lib.status import CheckStatus
from coveo_stew.environment import PythonEnvironment


@dataclass
class CheckResults:
    """Holds the result of a check execution."""

    name: str
    status: CheckStatus = CheckStatus.NotRan
    exit_code: Optional[int] = None
    output: List[str] = field(default_factory=list)
    exception: Optional[Exception] = None
    environment: Optional[PythonEnvironment] = None
    duration_seconds: Optional[float] = None

    def get_output_string(self) -> str:
        return "\n".join(self.output).strip()

    def create_test_case(self, name: str, classname: str) -> TestCase:
        test_case = TestCase(name, classname=classname)
        if self.status is CheckStatus.Error:
            test_case.add_error_info(
                "An error occurred, the check was unable to complete.",
                str(self.exception),
            )
        elif self.status is CheckStatus.CheckFailed:
            test_case.add_failure_info(
                "The check completed; errors were found.", "\n".join(self.output)
            )
        return test_case
