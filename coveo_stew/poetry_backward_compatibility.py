from functools import lru_cache
from typing import Callable, Dict, Optional

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
