from cleo.io.inputs.argument import Argument
from cleo.io.inputs.option import Option

from coveo_stew import commands
from coveo_stew.ui.poetry.base_command import StewBaseCommand


class CiCommand(StewBaseCommand):
    name = "stew ci"

    help = "Run CI checks on projects."

    arguments = [
        Argument(
            "project-name",
            required=False,
            is_list=False,
            description="The name of the project to run CI checks on. If not provided, all projects will be checked.",
        )
    ]

    options = [
        Option(
            "exact-match",
            description="Only match projects with the exact specified name rather than substring matching.",
        ),
        Option("fix", description="Fix issues found during CI checks where possible."),
        Option(
            "check",
            is_list=True,
            flag=False,
            description="Specify which checks to run (e.g., pytest, black, mypy).",
        ),
        Option("skip", is_list=True, flag=False, description="Specify which checks to skip."),
        Option(
            "quick",
            description="Do not call 'poetry install --sync' before testing. A quick preset may be defined in the pyproject file.",
        ),
        Option("sequential", description="Run checks sequentially instead of in parallel."),
        Option("github-step-report", description="Generate GitHub step report output."),
        Option(
            "extra",
            is_list=True,
            flag=False,
            description="Additional extras to include when testing.",
        ),
        Option("no-extras", description="Don't use any extras when testing."),
        Option("all-extras", description="Use all extras when testing."),
    ]

    def run_stew_command(self) -> int:
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
            io=self.io,
            project_name=project_name,
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
            disable_cache=self.option("no-cache"),
        )

        return 0
