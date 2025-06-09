from cleo.io.inputs.argument import Argument

from coveo_stew import commands
from coveo_stew.ui.poetry.base_command import StewBaseCommand


class LocateCommand(StewBaseCommand):
    name = "stew locate"

    help = "Locate a project in the workspace."

    arguments = [
        Argument(
            "project-name",
            required=True,
            is_list=False,
            description="The name of the project to locate in the workspace.",
        )
    ]

    def run_stew_command(self) -> int:
        project_name = self.argument("project-name")
        verbose = self.io.is_verbose()
        commands.locate(
            io=self.io,
            project_name=project_name,
            verbose=verbose,
            disable_cache=self.option("no-cache"),
        )
        return 0
