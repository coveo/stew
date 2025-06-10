from typing import Final

_running_as_plugin: bool = False


class _Context:
    """A class to manage misc states."""

    is_running_as_poetry_plugin: bool = False


context: Final = _Context()
