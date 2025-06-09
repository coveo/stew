from cleo.io.inputs.argument import Argument
from cleo.io.inputs.option import Option

from coveo_stew import commands
from coveo_stew.ui.poetry.base_command import StewBaseCommand


class FixOutdatedCommand(StewBaseCommand):
    name = "stew fix-outdated"

    help = "Fix outdated files in projects."

    arguments = [
        Argument(
            "project-name",
            required=False,
            is_list=False,
            description="The name of the project to fix outdated dependencies. If not provided, all projects will be processed.",
        )
    ]

    options = [
        Option(
            "exact-match",
            description="Only match projects with the exact specified name rather than substring matching.",
        ),
    ]

    def run_stew_command(self) -> int:
        project_name = self.argument("project-name")
        exact_match = self.option("exact-match")
        verbose = self.io.is_verbose()
        commands.fix_outdated(
            io=self.io,
            project_name=project_name,
            exact_match=exact_match,
            verbose=verbose,
            disable_cache=self.option("no-cache"),
        )
        return 0
