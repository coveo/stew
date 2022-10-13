from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Type, TypeVar, Union

from coveo_functools.casing import flexfactory
from typing_extensions import Final

T = TypeVar("T")


class Dependency:
    """A poetry-style package dependency, such as `mypy = '*'` or 'cdf = { path = "../cdf" }`"""

    def __init__(
        self,
        name: str,
        optional: bool = False,
        path: Union[Path, str] = None,
        version: str = "*",
        extras: List[str] = None,
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


class PoetryAPI:
    """Represents the poetry-specific sections of a pyproject.toml file."""

    def __init__(
        self,
        *,
        name: str,
        version: str,
        description: str,
        authors: Iterable[str],
        dependencies: Mapping[str, Any] = None,
        dev_dependencies: Mapping[str, Any] = None,
        group: Mapping[str, Any] = None,
        **extra: Any,
    ) -> None:
        self.name: Final[str] = name
        self.safe_name: Final[str] = name.replace("-", "_")
        self.authors: Final[Iterable[str]] = authors
        self.version: Final[str] = version
        self.description: Final[str] = description

        deps = dependencies_factory(dependencies)
        dev_deps = dependencies_factory(dev_dependencies)

        if group:
            # poetry 1.2 adds dependency groups.
            for group_name, items in group.items():
                if group_deps := items.get("dependencies"):
                    # note: based on the docs, we are moving away from having "dev" dependencies at all...
                    (dev_deps if group_name == "dev" else deps).update(
                        dependencies_factory(group_deps)
                    )

        self.dependencies: Final[Mapping[str, Dependency]] = deps
        self.dev_dependencies: Final[Mapping[str, Dependency]] = dev_deps

        # extra will contain all other properties of the package, mainly for dev/debug purposes.
        self.extra: Final[Mapping[str, Any]] = extra

    @property
    def all_dependencies(self) -> Mapping[str, Dependency]:
        """Gathers dependencies and dev dependencies. If a dependency is duplicated in both sections, the dev ones
        take precedence."""
        return {**self.dependencies, **self.dev_dependencies}


def dependencies_factory(
    dependencies: Mapping[str, Union[str, dict]] = None
) -> Dict[str, Dependency]:
    """Transforms a poetry dependency section (such as tool.poetry.dev-dependencies) into Dependency instances."""
    return (
        {name: Dependency.factory(name, dependency) for name, dependency in dependencies.items()}
        if dependencies
        else {}
    )
