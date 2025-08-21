import shutil
import tempfile
from pathlib import Path
from typing import Any

from coveo_styles.styles import echo
from coveo_systools.filesystem import pushd
from coveo_systools.subprocess import async_check_output

from coveo_stew.ci.checks.lib.base_check import BaseCheck
from coveo_stew.ci.checks.lib.status import CheckStatus
from coveo_stew.environment import PythonEnvironment, PythonTool


class CheckOutdated(BaseCheck):
    name: str = "check-outdated"

    async def _do_check(self, environment: PythonEnvironment, **kwargs: Any) -> CheckStatus:
        if self._pyproject.lock_is_outdated():
            self.result.output.append('The lock file is out of date: run "stew fix-outdated"')
            return CheckStatus.CheckFailed
        return CheckStatus.Success


class CheckOfflineBuild(BaseCheck):
    name: str = "poetry-build"

    async def _do_check(self, environment: PythonEnvironment, **kwargs: Any) -> CheckStatus:
        temporary_folder = Path(tempfile.mkdtemp())
        offline_install_location = temporary_folder / "wheels"

        try:
            output = await async_check_output(
                *environment.build_command(
                    PythonTool.Stew,
                    "build",
                    "--target",
                    offline_install_location,
                    "--python",
                    environment.python_executable,
                ),
                remove_ansi=False,
                **kwargs,
            )
            self.result.output.extend(output.splitlines())

            # make sure pip install finds everything it needs from the offline location.
            # move out to a controlled file structure so that no folder imports are possible
            with pushd(temporary_folder):
                output = await async_check_output(
                    *environment.build_command(
                        PythonTool.Pip,
                        "install",
                        self._pyproject.poetry.package.name,
                        "--no-cache",
                        "--no-index",
                        "--find-links",
                        offline_install_location,
                        "--target",
                        temporary_folder / "pip-install-test",
                        (
                            "--pre"
                            if any(p.allows_prereleases for p in self._pyproject.dependencies)
                            else ""
                        ),
                    ),
                    remove_ansi=False,
                    **kwargs,
                )

            self.result.output.extend(output.splitlines())

        finally:
            try:
                shutil.rmtree(temporary_folder)
            except PermissionError:
                echo.warning(
                    f"The temporary folder for this check could not be deleted: {temporary_folder}"
                )

        return CheckStatus.Success
