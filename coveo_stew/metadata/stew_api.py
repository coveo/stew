from typing import Mapping, Any

from coveo_stew.metadata.poetry_api import dependencies_factory


class StewPackage:
    """Represents the coveo-specific sections of a pyproject.toml file."""

    def __init__(
        self,
        *,
        build: bool = False,
        pydev: bool = False,
        build_dependencies: Mapping[str, Any] = None
    ) -> None:
        self.build = build  # we won't build a project unless this is specified.
        self.pydev = pydev  # is this a one-ring-to-bind-them-all dev environment?
        # additional build-time dependencies
        self.build_dependencies = dependencies_factory(build_dependencies)
