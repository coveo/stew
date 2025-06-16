from coveo_stew import commands
from coveo_stew.ui.poetry.base_command import StewBaseCommand


class VersionCommand(StewBaseCommand):
    name = "stew version"

    help = "Show the coveo-stew version"

    def run_stew_command(self) -> int:
        commands.version(io=self.io)
        return 0
