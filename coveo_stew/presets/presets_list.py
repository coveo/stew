from typing import Callable

from coveo_stew.presets.presets import clean_imports, ruff

STEW_PRESETS_LIST: list[tuple[Callable, str]] = [
    (clean_imports, "Adds isort and autoflake to sort and clean imports."),
    (ruff, "Replaces black and mypy by ruff-format, ruff-check and ruff-isort."),
]
