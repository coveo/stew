from cleo.descriptors.text_descriptor import TextDescriptor
from cleo.io.io import IO
from poetry.console.application import Application

from coveo_stew.ui.poetry.base_command import StewBaseCommand


class StewCommand(StewBaseCommand):
    name = "stew"

    help = "Opinionated python development utilities."

    application: Application
    io: IO

    def run_stew_command(self) -> int:
        # for some reason, calling `self.call("stew", "--help")` doesn't show the help text.
        # so we manually describe the command here :shrug:
        self.io.write_line("")
        TextDescriptor().describe(self.io, self)
        return 0
