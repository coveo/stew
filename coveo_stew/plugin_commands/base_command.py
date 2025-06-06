import os
from abc import abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from cleo.commands.command import Command
from coveo_styles.styles import ExitWithFailure
from coveo_systools.filesystem import pushd


class StewBaseCommand(Command):
    """Base class for all Stew commands that provides common functionality."""

    @abstractmethod
    def run_stew_command(self) -> int:
        """Override with the actual command."""

    def handle(self) -> int:
        """
        Poetry Plugin's entry point.
        We abstract this one to handle common stew setup and teardown logic.
        """
        with self._setup():
            return self.run_stew_command()

    @contextmanager
    def _setup(self) -> Generator[None, None, None]:
        """Setup & Cleanup orchestrator."""
        with self._setup_project_directory():
            yield

    @contextmanager
    def _setup_project_directory(self) -> Generator[None, None, None]:
        """
        Manages the working directory if the --project option is specified.

        For some reason, poetry handles the `--directory` option for us, but not the `--project` option.
        https://python-poetry.org/docs/cli/#global-options
        """
        if self.option("project"):
            # definition from the docs:
            #  - Specify another path as the project root.
            #  - All command-line arguments will be resolved relative to the current working directory
            #    or directory specified using --directory option if used.
            #
            # In our case, the `--directory` option is already applied by poetry (it's already the cwd).
            # Therefore, we only need to handle `--project`:
            project_location = Path(os.getcwd()) / self.option("project")

            if not project_location.exists():
                raise ExitWithFailure(
                    failures=[f"Project location doesn't exist: {project_location}"],
                    suggestions=[
                        "Make sure you are in the correct directory.",
                        "The `--project|-P` option is relative to the `--directory` option or the current working directory.",
                        f"Stew can locate the project in nested directories using the package name: `stew {self.name.split()[-1]} <package-name>`",
                    ],
                )
            if not project_location.is_dir():
                project_location = project_location.parent

            with pushd(project_location):
                yield
        else:
            yield
