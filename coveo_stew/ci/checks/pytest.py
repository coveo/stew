from cleo.io.io import IO

from coveo_stew.ci.checks.lib.cli_check import CLICheck
from coveo_stew.stew import PythonProject


class CheckPytest(CLICheck):
    name: str = "pytest"
    check_failed_exit_codes = [1]
    outputs_own_report = True

    def __init__(
        self,
        io: IO,
        *,
        marker_expression: str = None,
        doctest_modules: bool = True,
        _pyproject: PythonProject,
    ) -> None:

        check_args = [
            "--color=yes",
            "--durations=5",
            "--tb=short",
            # todo: the report path relies on the environment but it has not been assigned yet?
            # f"--junitxml={self.report_path(self.result)}"
        ]
        if marker_expression:
            check_args.extend(("-m", marker_expression))
        if doctest_modules:
            check_args.append("--doctest-modules")

        super().__init__(
            io,
            name="pytest",
            check_args=check_args,
            create_generic_report=False,
            _pyproject=_pyproject,
        )
