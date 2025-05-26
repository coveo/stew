from cleo.commands.command import Command
from cleo.io.inputs.argument import Argument
from cleo.io.inputs.option import Option
from cleo.io.io import IO
from poetry.console.application import Application
from poetry.plugins.application_plugin import ApplicationPlugin

from coveo_stew import commands


class BumpCommand(Command):
    name = "stew bump"

    arguments = [Argument("project-name", required=False)]

    options = [
        Option("exact-match"),
    ]

    def handle(self) -> int:
        self.line("Hello from Bump!")
        commands.bump(
            self.io,
            self.argument("project-name"),
            exact_match=self.option("exact-match"),
            verbose=self.io.is_verbose(),
        )
        return 0


class VersionCommand(Command):
    name = "stew version"

    def handle(self) -> int:
        commands.version(self.io)
        return 0


class CheckOutdatedCommand(Command):
    name = "stew check-outdated"

    arguments = [Argument("project-name", required=False, is_list=False)]

    options = [
        Option("exact-match"),
    ]

    def handle(self) -> int:
        project_name = self.argument("project-name")
        exact_match = self.option("exact-match")
        verbose = self.io.is_verbose()
        commands.check_outdated(self.io, project_name, exact_match=exact_match, verbose=verbose)
        return 0


class FixOutdatedCommand(Command):
    name = "stew fix-outdated"

    arguments = [Argument("project-name", required=False, is_list=False)]

    options = [
        Option("exact-match"),
    ]

    def handle(self) -> int:
        project_name = self.argument("project-name")
        exact_match = self.option("exact-match")
        verbose = self.io.is_verbose()
        commands.fix_outdated(self.io, project_name, exact_match=exact_match, verbose=verbose)
        return 0


class BuildCommand(Command):
    name = "stew build"

    arguments = [Argument("project-name", required=False, is_list=False)]

    options = [
        # Unlike all other commands, exact match is true by default to retain
        # the original behavior which required a project name to be specified exactly.
        Option("exact-match"),
        Option("directory", flag=False),
        Option("python", flag=False),
    ]

    def handle(self) -> int:
        project_name = self.argument("project-name")
        exact_match = self.option("exact-match")
        verbose = self.io.is_verbose()
        directory = self.option("directory")
        python = self.option("python")
        commands.build(
            self.io,
            project_name,
            exact_match=exact_match,
            directory=directory,
            python=python,
            verbose=verbose,
        )
        return 0


class FreshEggsCommand(Command):
    name = "stew fresh-eggs"

    arguments = [Argument("project-name", required=False, is_list=False)]

    options = [
        Option("exact-match"),
    ]

    def handle(self) -> int:
        project_name = self.argument("project-name")
        exact_match = self.option("exact-match")
        verbose = self.io.is_verbose()
        commands.fresh_eggs(self.io, project_name, exact_match=exact_match, verbose=verbose)
        return 0


class PullDevRequirementsCommand(Command):
    name = "stew pull-dev-requirements"

    options = [
        Option("dry-run"),
    ]

    def handle(self) -> int:
        dry_run = self.option("dry-run")
        verbose = self.io.is_verbose()
        commands.pull_dev_requirements(self.io, dry_run=dry_run, verbose=verbose)
        return 0


class LocateCommand(Command):
    name = "stew locate"

    arguments = [Argument("project-name", required=True, is_list=False)]

    def handle(self) -> int:
        project_name = self.argument("project-name")
        verbose = self.io.is_verbose()
        commands.locate(self.io, project_name, verbose=verbose)
        return 0


class RefreshCommand(Command):
    name = "stew refresh"

    arguments = [Argument("project-name", required=False, is_list=False)]

    options = [
        Option("exact-match"),
    ]

    def handle(self) -> int:
        project_name = self.argument("project-name")
        exact_match = self.option("exact-match")
        verbose = self.io.is_verbose()
        commands.refresh(self.io, project_name, exact_match=exact_match, verbose=verbose)
        return 0


class CiCommand(Command):
    name = "stew ci"

    arguments = [Argument("project-name", required=False, is_list=False)]

    options = [
        Option("exact-match"),
        Option("fix"),
        Option("check", is_list=True, flag=False),
        Option("skip", is_list=True, flag=False),
        Option("quick", description="Do not call 'poetry install --sync' before testing."),
        Option("sequential"),
        Option("github-step-report"),
        Option("extra", is_list=True, flag=False),
        Option("no-extras"),
        Option("all-extras"),
    ]

    def handle(self) -> int:
        project_name = self.argument("project-name")
        exact_match = self.option("exact-match")
        fix = self.option("fix")
        check = self.option("check")
        skip = self.option("skip")
        verbose = self.io.is_verbose()
        quick = self.option("quick")
        parallel = not self.option("sequential")
        github_step_report = self.option("github-step-report")
        extra = self.option("extra")
        no_extras = self.option("no-extras")
        all_extras = self.option("all-extras")

        commands.ci(
            self.io,
            project_name,
            exact_match=exact_match,
            fix=fix,
            check=check,
            skip=skip,
            verbose=verbose,
            quick=quick,
            parallel=parallel,
            github_step_report=github_step_report,
            extra=extra,
            no_extras=no_extras,
            all_extras=all_extras,
        )
        return 0


class StewCommand(Command):
    name = "stew"

    application: Application
    io: IO

    def handle(self) -> int:
        self.line("Hello from Stew!")
        if not self.option("help"):
            self.call("stew", "--help")
        return 0


COMMANDS: list[type[Command]] = [
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


class StewPlugin(ApplicationPlugin):
    def activate(self, application: Application) -> None:
        for command_class in COMMANDS:
            application.command_loader.register_factory(command_class.name, command_class)
