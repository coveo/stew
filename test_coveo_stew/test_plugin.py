import pytest
from cleo.testers.command_tester import CommandTester
from coveo_systools.filesystem import pushd
from coveo_testing.parametrize import parametrize
from poetry.console.application import Application

from coveo_stew.plugin_commands.build_command import BuildCommand
from coveo_stew.plugin_commands.bump_command import BumpCommand
from coveo_stew.plugin_commands.check_outdated_command import (
    CheckOutdatedCommand,
)
from coveo_stew.plugin_commands.ci_command import CiCommand
from coveo_stew.plugin_commands.fix_outdated_command import FixOutdatedCommand
from coveo_stew.plugin_commands.fresh_eggs_command import FreshEggsCommand
from coveo_stew.plugin_commands.locate_command import LocateCommand
from coveo_stew.plugin_commands.pull_dev_requirements_command import (
    PullDevRequirementsCommand,
)
from coveo_stew.plugin_commands.refresh_command import RefreshCommand
from coveo_stew.plugin_commands.stew_command import StewCommand
from coveo_stew.plugin_commands.version_command import VersionCommand
from coveo_stew.poetry_plugin import StewPlugin

COMMNANDS = [
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
]


@pytest.fixture
def app() -> Application:
    application = Application()
    StewPlugin().activate(application)
    return application


@pytest.fixture
def stew(app: Application) -> CommandTester:
    command = app.find("stew")
    return CommandTester(command)


@parametrize("command_name", (command.name for command in COMMNANDS))
def test_stew_plugin_command_names(command_name: str, app: Application) -> None:
    assert command_name.islower()
    assert command_name.startswith("stew")
    assert command_name.strip() == command_name
    if command_name != "stew":
        assert len(command_name.split(" ")) == 2


@parametrize("command_name", (command.name for command in COMMNANDS))
def test_stew_plugin_commands_hooked_up(command_name: str, app: Application) -> None:
    _ = app.find(command_name)  # will crash if not registered


def test_stew_plugin_no_duplicate_commands(app: Application) -> None:
    command_names = [command.name for command in COMMNANDS]
    assert len(command_names) == len(set(command_names)), "Duplicate commands found!"


def test_stew_plugin_usage(stew: CommandTester) -> None:
    stew.execute()
    assert stew.status_code == 0
    assert stew.io.fetch_output().strip().startswith("Usage:")


@pytest.mark.skip("Example how to debug commands targetting another project locally.")
def test_stew_bespoke(app: Application) -> None:
    command = app.find("stew pull-dev-requirements")
    command_tester = CommandTester(command)
    with pushd("/Users/jpiche/code/security-siem"):
        command_tester.execute()

    assert command_tester.status_code == 0
