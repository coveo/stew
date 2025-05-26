import pytest
from cleo.testers.command_tester import CommandTester
from coveo_systools.filesystem import pushd
from poetry.console.application import Application

from coveo_stew.poetry_plugin import StewPlugin


@pytest.fixture
def app() -> Application:
    application = Application()
    StewPlugin().activate(application)
    return application


@pytest.fixture
def stew(app: Application) -> CommandTester:
    command = app.find("stew bump")
    return CommandTester(command)


def test_stew_plugin_hooks_up(app: Application) -> None:
    _ = app.find("stew")  # will crash if not registered


def test_stew_plugin_subcommand_hooks_up(app: Application) -> None:
    _ = app.find("stew bump")  # will crash if not registered


def test_stew_plugin_usage(stew: CommandTester) -> None:
    stew.execute()
    assert stew.status_code == 0
    assert stew.io.fetch_output() == "Hello from Bump!\n"


def test_stew_bespoke(app: Application) -> None:
    command = app.find("stew pull-dev-requirements")
    command_tester = CommandTester(command)
    with pushd("/Users/jpiche/code/coveo-python-oss"):
        command_tester.execute()

    assert command_tester.status_code == 0
