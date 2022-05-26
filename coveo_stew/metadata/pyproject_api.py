from pathlib import Path
from typing import Optional, TYPE_CHECKING, Iterator
from typing_extensions import Protocol

from poetry.poetry import Poetry


if TYPE_CHECKING:
    from coveo_stew.environment import PythonEnvironment
    from coveo_stew.metadata.stew_api import StewPackage
    from coveo_stew.metadata.poetry_api import PoetryAPI


class PythonProjectAPI(Protocol):
    verbose: bool
    project_path: Path
    toml_path: Path
    package: "PoetryAPI"
    options: "StewPackage"
    lock_path: Path
    egg_path: Path
    poetry: Poetry
    repo_root: Optional[Path]

    def __init__(self, project_path: Path, *, verbose: bool = False) -> None:
        ...

    def virtual_environments(
        self, *, create_default_if_missing: bool = False
    ) -> Iterator["PythonEnvironment"]:
        ...

    def install(
        self,
        *,
        environment: "PythonEnvironment" = None,
        remove_untracked: bool = True,
        quiet: bool = False
    ) -> None:
        ...

    def build(self, target_path: Path) -> Path:
        ...

    @property
    def lock_is_outdated(self) -> bool:
        ...
