from cleo.io.inputs.argument import Argument
from cleo.io.inputs.option import Option
from coveo_styles.styles import ExitWithFailure

from coveo_stew import commands
from coveo_stew.ui.poetry.base_command import StewBaseCommand


class BuildCommand(StewBaseCommand):
    name = "stew build"

    help = "Store the project and its locked dependencies to disk for offline installation."

    arguments = [
        Argument(
            "project-name",
            required=False,
            is_list=False,
            description="The name of the project to build. If not provided, all projects will be built.",
        )
    ]

    options = [
        # Option("directory", "C", flag=False),  # this one is built-in, poetry will chdir before calling us.
        # Option("project", "P", flag=False),  # this one is built-in, but we need to handle it ourselves.
        Option("python", flag=False, description="The python executable to use."),
        Option(
            "target", flag=False, description="Directory where the built wheels should be stored."
        ),
    ]

    def run_stew_command(self) -> int:
        if self.option("directory") is not None:
            raise ExitWithFailure(
                failures=[
                    "Stew's `--directory` option conflicts with Poetry's built-in `--directory` option.",
                    "The `--directory` option was renamed to `--target` in coveo-stew 4.0.0.",
                ],
                suggestions=[
                    "Use `--target` instead of `--directory` to specify where wheels should be stored.",
                    "Use `--project` instead of `--directory` if you are trying to change the working directory for the command.",
                    "Eventually, Poetry's `--directory` option will be restored. It is currently disabled as a courtesy notice for users who may have been using it.",
                ],
            )

        commands.build(
            io=self.io,
            project_name=self.argument("project-name"),
            # `stew build` forces `--exact-match`, unlike all other commands.
            exact_match=True,
            directory=self.option("target"),
            python=self.option("python"),
            #  The `io` object is automatically configured with poetry's builtin `-vvv` flags.
            verbose=self.io.is_verbose(),
            disable_cache=self.option("no-cache"),
        )
        return 0
