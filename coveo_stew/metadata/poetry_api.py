from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Type, TypeVar, Union

from coveo_functools.casing import flexfactory

T = TypeVar("T")


class Dependency:
    """A poetry-style package dependency, such as `mypy = '*'` or 'cdf = { path = "../cdf" }`"""

    def __init__(
        self,
        name: str,
        optional: bool = False,
        path: Union[Path, str] = None,
        version: str = "*",
        extras: Iterable[str] = None,
        source: str = None,
        allow_prerelease: bool = None,
    ) -> None:
        # set some defaults
        self.name = name
        self.optional = optional
        self.path: Optional[Path] = Path(path) if isinstance(path, str) else path
        self.version = version
        self.extras = extras
        self.source = source
        self.allow_prereleases = allow_prerelease

    @property
    def is_local(self) -> bool:
        return self.path is not None

    @classmethod
    def factory(cls: Type[T], name: str, dependency: Union[str, Dict[str, Any]]) -> T:
        if isinstance(dependency, str):
            dependency = {"name": name, "version": dependency}
        else:
            dependency["name"] = name
        return flexfactory(cls, **dependency)


def dependencies_factory(
    dependencies: Mapping[str, Union[str, dict]] = None,
) -> Dict[str, Dependency]:
    """Transforms a poetry dependency section (such as tool.poetry.dev-dependencies) into Dependency instances."""
    return (
        {name: Dependency.factory(name, dependency) for name, dependency in dependencies.items()}
        if dependencies
        else {}
    )
