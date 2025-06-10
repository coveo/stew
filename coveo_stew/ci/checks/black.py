from cleo.io.io import IO

from coveo_stew.ci.checks.lib.cli_check import CLICheck
from coveo_stew.stew import PythonProject


class CheckBlack(CLICheck):

    def __init__(self, io: IO, *, _pyproject: PythonProject) -> None:
        super().__init__(
            io,
            name="black",
            create_generic_report=True,
            check_args=[".", "--check"],
            autofix_args=".",
            _pyproject=_pyproject,
        )
