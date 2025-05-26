from coveo_stew import commands
from coveo_stew.plugin_commands.base_command import StewBaseCommand


class VersionCommand(StewBaseCommand):
    name = "stew version"

    def run_stew_command(self) -> int:
        commands.version(self.io)
        return 0
