import shutil
import tempfile
from pathlib import Path

from coveo_systools.filesystem import pushd
from coveo_systools.subprocess import async_check_output

from coveo_stew.ci.runner import ContinuousIntegrationRunner, RunnerStatus
from coveo_stew.environment import PythonEnvironment, PythonTool
from coveo_stew.offline_publish import offline_publish


class CheckOutdatedRunner(ContinuousIntegrationRunner):
    name: str = "check-outdated"

    async def _launch(self, environment: PythonEnvironment, *extra_args: str) -> RunnerStatus:
        if self._pyproject.lock_is_outdated():
            self._last_output = ['The lock file is out of date: run "stew fix-outdated"']
            return RunnerStatus.CheckFailed
        return RunnerStatus.Success


class OfflineInstallRunner(ContinuousIntegrationRunner):
    name: str = "poetry-build"

    async def _launch(self, environment: PythonEnvironment, *extra_args: str) -> RunnerStatus:
        temporary_folder = Path(tempfile.mkdtemp())
        offline_install_location = temporary_folder / "wheels"

        try:
            # publish the offline wheels
            offline_publish(self._pyproject, offline_install_location, environment, quiet=False)

            # make sure pip install finds everything it needs from the offline location.
            # move out to a controlled file structure so that no folder imports are possible
            with pushd(temporary_folder):
                await async_check_output(
                    *environment.build_command(
                        PythonTool.Pip,
                        "install",
                        self._pyproject.package.name,
                        "--no-cache",
                        "--no-index",
                        "--find-links",
                        offline_install_location,
                        "--target",
                        temporary_folder / "pip-install-test",
                        "--pre"
                        if any(
                            p.allow_prereleases
                            for p in self._pyproject.package.dependencies.values()
                        )
                        else "",
                    ),
                )
        finally:
            shutil.rmtree(temporary_folder)

        return RunnerStatus.Success
