from pathlib import Path
from typing import Any, MutableMapping

import toml
from coveo_styles.styles import ExitWithFailure
from toml import TomlDecodeError


def load_toml_from_path(toml_path: Path) -> MutableMapping[str, Any]:
    """Loads a toml from path or raise ExitWithFailure on failure."""
    return _load_toml_from_content(toml_path.read_text(), toml_path)


def _load_toml_from_content(toml_content: str, toml_path: Path) -> MutableMapping[str, Any]:
    try:
        return toml.loads(toml_content)
    except TomlDecodeError as ex:
        lineno, colno = ex.lineno, ex.colno
        raise ExitWithFailure(suggestions=f"{toml_path}:{lineno}:{colno} parse error") from ex
