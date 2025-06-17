from coveo_stew import commands
from coveo_stew.ui.poetry.base_command import StewBaseCommand


class PresetsCommand(StewBaseCommand):
    name = "stew presets"

    help = "Shows the builtin stew presets."

    def run_stew_command(self) -> int:
        commands.presets_list(self.io)
        return 0
