"""
This file is loaded by Poetry when it starts up.

In order to keep performance optimal:
 - we use strings for type hints
 - we only import the commands when the plugin is activated.

Doing it as such will ensure that the plugin doesn't slow down or impact Poetry when it isn't used.
"""

from typing import TYPE_CHECKING

from poetry.plugins.application_plugin import ApplicationPlugin

if TYPE_CHECKING:
    from poetry.console.application import Application


class StewPlugin(ApplicationPlugin):
    def activate(self, application: "Application") -> None:
        from coveo_stew.ui.poetry.build_command import BuildCommand
        from coveo_stew.ui.poetry.bump_command import BumpCommand
        from coveo_stew.ui.poetry.check_outdated_command import (
            CheckOutdatedCommand,
        )
        from coveo_stew.ui.poetry.ci_command import CiCommand
        from coveo_stew.ui.poetry.fix_outdated_command import FixOutdatedCommand
        from coveo_stew.ui.poetry.fresh_eggs_command import FreshEggsCommand
        from coveo_stew.ui.poetry.locate_command import LocateCommand
        from coveo_stew.ui.poetry.pull_dev_requirements_command import (
            PullDevRequirementsCommand,
        )
        from coveo_stew.ui.poetry.refresh_command import RefreshCommand
        from coveo_stew.ui.poetry.stew_command import StewCommand
        from coveo_stew.ui.poetry.version_command import VersionCommand

        for command_class in [
            StewCommand,
            BumpCommand,
            VersionCommand,
            CheckOutdatedCommand,
            FixOutdatedCommand,
            BuildCommand,
            FreshEggsCommand,
            PullDevRequirementsCommand,
            LocateCommand,
            RefreshCommand,
            CiCommand,
        ]:
            application.command_loader.register_factory(command_class.name, command_class)
