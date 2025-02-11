from functools import lru_cache
from typing import Callable, Dict, List, Optional

from packaging.version import Version

from coveo_stew.environment import PythonEnvironment, find_poetry_version

VerbPredicate = Callable[[Version], bool]


VERBS: Dict[str, Dict[VerbPredicate, str]] = {
    "--sync": {(lambda v: v < Version("1.2.0")): "--remove-untracked"}
}


@lru_cache
def get_verb(verb: str, environment: Optional[PythonEnvironment]) -> str:
    if verb not in VERBS:
        return verb

    poetry_version = find_poetry_version(environment)
    for predicate, old_verb in VERBS[verb].items():
        if predicate(poetry_version):
            return old_verb

    return verb


def get_install_sync_command(sync_target_environment: Optional[PythonEnvironment]) -> List[str]:
    """Returns the `poetry install --sync` command equivalent for this version of poetry."""
    if find_poetry_version(sync_target_environment) >= Version("2.0.0"):
        # 2.0.0 ditched "poetry install --sync" for "poetry sync"
        return ["sync"]

    # backward compatibility
    # 1.2.0 and below use `poetry install --remove-untracked` flag
    # 1.2.1 renamed `--remove-untracked` to `--sync`
    return ["install", get_verb("--sync", sync_target_environment)]
