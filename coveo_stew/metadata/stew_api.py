from typing import Any, Dict, List, Mapping, Optional

from coveo_styles.styles import echo

from coveo_stew.metadata.poetry_api import dependencies_factory


class StewPackage:
    """Represents the stew-specific sections of a pyproject.toml file."""

    def __init__(
        self,
        *,
        build_without_hashes: bool = False,
        pydev: bool = False,
        build_dependencies: Optional[Mapping[str, Any]] = None,
        extras: Optional[List[str]] = None,
        quick: Optional[Dict[str, Any]] = None,
        all_extras: bool = False,
    ) -> None:
        # poetry sometimes fail at getting hashes, in which case the export cannot work because pip will complain
        # that some files have a hash and some don't. This fixes it.
        self.build_without_hashes = build_without_hashes
        self.pydev = pydev  # is this a one-ring-to-bind-them-all dev environment?
        # additional build-time dependencies
        self.build_dependencies = dependencies_factory(build_dependencies)
        self.extras = extras
        self.all_extras = all_extras
        self.quick = quick or {}

        if extras and all_extras:
            echo.suggest(
                "Both 'extras' and 'all_extras' are specified. 'extras' will be ignored; "
                "consider removing it from your pyproject.toml."
            )
