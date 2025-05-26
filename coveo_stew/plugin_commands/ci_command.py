from cleo.io.inputs.argument import Argument
from cleo.io.inputs.option import Option

from coveo_stew import commands
from coveo_stew.plugin_commands.base_command import StewBaseCommand


class CiCommand(StewBaseCommand):
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
