from cleo.io.inputs.argument import Argument

from coveo_stew import commands
from coveo_stew.plugin_commands.base_command import StewBaseCommand


class LocateCommand(StewBaseCommand):
    name = "stew locate"

    arguments = [Argument("project-name", required=True, is_list=False)]

    def run_stew_command(self) -> int:
        project_name = self.argument("project-name")
        verbose = self.io.is_verbose()
        commands.locate(self.io, project_name, verbose=verbose)
        return 0
