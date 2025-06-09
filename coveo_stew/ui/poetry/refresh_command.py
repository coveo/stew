from cleo.io.inputs.argument import Argument
from cleo.io.inputs.option import Option

from coveo_stew import commands
from coveo_stew.ui.poetry.base_command import StewBaseCommand


class RefreshCommand(StewBaseCommand):
    name = "stew refresh"

    help = "Update the lock files and the virtual environments."

    arguments = [
        Argument(
            "project-name",
            required=False,
            is_list=False,
            description="The name of the project to refresh. If not provided, all projects will be refreshed.",
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
        commands.refresh(
            io=self.io,
            project_name=project_name,
            exact_match=exact_match,
            verbose=verbose,
            disable_cache=self.option("no-cache"),
        )
        return 0
