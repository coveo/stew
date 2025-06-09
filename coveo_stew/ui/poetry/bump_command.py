from cleo.io.inputs.argument import Argument
from cleo.io.inputs.option import Option

from coveo_stew import commands
from coveo_stew.ui.poetry.base_command import StewBaseCommand


class BumpCommand(StewBaseCommand):
    name = "stew bump"

    help = "Updates lock files."

    arguments = [
        Argument(
            "project-name",
            required=False,
            description="The name of the project to bump version. If not provided, all projects will be processed.",
        )
    ]

    options = [
        Option(
            "exact-match",
            description="Only match projects with the exact specified name rather than substring matching.",
        ),
    ]

    def run_stew_command(self) -> int:
        commands.bump(
            io=self.io,
            project_name=self.argument("project-name"),
            exact_match=self.option("exact-match"),
            verbose=self.io.is_verbose(),
            disable_cache=self.option("no-cache"),
        )
        return 0
