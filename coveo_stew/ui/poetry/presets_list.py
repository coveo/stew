from coveo_stew import commands
from coveo_stew.plugin_commands.base_command import StewBaseCommand


class PresetsListCommand(StewBaseCommand):
    name = "stew presets list"

    help = "Shows the builtin stew presets."

    def run_stew_command(self) -> int:
        commands.presets_list(self.io)
        return 0
