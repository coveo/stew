from typing import Any, Mapping

from coveo_stew.metadata.poetry_api import dependencies_factory


class StewPackage:
    """Represents the coveo-specific sections of a pyproject.toml file."""

    def __init__(
        self,
        *,
        build: bool = False,
        build_without_hashes: bool = False,
        pydev: bool = False,
        build_dependencies: Mapping[str, Any] = None
    ) -> None:
        self.build = build  # we won't build a project unless this is specified.
        # poetry sometimes fail at getting hashes, in which case the export cannot work because pip will complain
        # that some files have a hash and some don't. This fixes it.
        self.build_without_hashes = build_without_hashes
        self.pydev = pydev  # is this a one-ring-to-bind-them-all dev environment?
        # additional build-time dependencies
        self.build_dependencies = dependencies_factory(build_dependencies)
