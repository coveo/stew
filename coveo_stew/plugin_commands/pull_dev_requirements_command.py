from cleo.io.inputs.option import Option

from coveo_stew import commands
from coveo_stew.plugin_commands.base_command import StewBaseCommand


class PullDevRequirementsCommand(StewBaseCommand):
    name = "stew pull-dev-requirements"

    help = "For Multiple Libraries: Pulls the development requirements from all local projects in the workspace into the pydev project at the root."

    options = [
        Option("dry-run", description="Show what would be done without making any changes."),
    ]

    def run_stew_command(self) -> int:
        dry_run = self.option("dry-run")
        verbose = self.io.is_verbose()
        commands.pull_dev_requirements(self.io, dry_run=dry_run, verbose=verbose)
        return 0
