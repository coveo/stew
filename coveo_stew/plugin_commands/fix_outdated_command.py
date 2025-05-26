from cleo.io.inputs.argument import Argument
from cleo.io.inputs.option import Option

from coveo_stew import commands
from coveo_stew.plugin_commands.base_command import StewBaseCommand


class FixOutdatedCommand(StewBaseCommand):
    name = "stew fix-outdated"

    arguments = [Argument("project-name", required=False, is_list=False)]

    options = [
        Option("exact-match"),
    ]

    def run_stew_command(self) -> int:
        project_name = self.argument("project-name")
        exact_match = self.option("exact-match")
        verbose = self.io.is_verbose()
        commands.fix_outdated(self.io, project_name, exact_match=exact_match, verbose=verbose)
        return 0
