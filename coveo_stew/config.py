from pprint import pformat
from types import ModuleType
from typing import Any, Callable, Mapping, Optional

from cleo.io.io import IO
from cleo.io.outputs.output import Verbosity
from coveo_itertools.lookups import dict_lookup
from coveo_styles.styles import ExitWithFailure

import coveo_stew.presets.presets as stew_presets


def normalize_key(key: str) -> str:
    """
    Normalize a dictionary key by replacing underscores with hyphens.
    Used to treat keys with underscores and hyphens as equivalent.
    """
    return key.replace("_", "-")


def merge(a: dict, b: dict) -> None:
    """
    Mutates `a` by merging `b` into it.
    Dicts and Lists are merged.
    Other values are overwritten.
    Treats keys with underscores and hyphens as equivalent (e.g., 'custom-runners' is the same as 'custom_runners').
    """
    # Create a map of normalized keys to original keys in 'a' for quick lookups
    normalized_keys_map = {normalize_key(k): k for k in a}

    for key in b:
        normalized_key = normalize_key(key)

        # Check if a normalized version of this key exists in 'a'
        if normalized_key in normalized_keys_map:
            original_key = normalized_keys_map[normalized_key]

            if isinstance(a[original_key], dict) and isinstance(b[key], dict):
                merge(a[original_key], b[key])
                continue
            elif isinstance(a[original_key], list) and isinstance(b[key], list):
                a[original_key].extend(b[key])
                continue

            # For non-containers, overwrite the value in 'a'
            a[original_key] = b[key]
        else:
            # Key doesn't exist in 'a', add it
            a[key] = b[key]


def load_config_from_presets(io: IO, data: Mapping[str, Any]) -> tuple[dict, dict]:
    """Loads the stew and ci sections from the given data."""
    stew_config = dict_lookup(data, "tool", "stew", default={})

    # always start with the default preset
    presets = ["default"]

    # add the user's presets
    defined_presets = stew_config.get("presets", [])
    if not isinstance(defined_presets, list):
        raise ExitWithFailure() from ValueError(
            f"Presets must be a list, got {type(defined_presets)}"
        )
    if not all(isinstance(preset, str) for preset in defined_presets):
        raise ExitWithFailure() from ValueError("All presets must be strings")
    presets.extend(defined_presets)
    io.write_line("Using presets: " + ", ".join(presets), verbosity=Verbosity.VERBOSE)

    # aggregate/merge the presets
    aggregated_config: dict = {}
    for preset_name in presets:
        merge(aggregated_config, load_preset(stew_presets, preset_name))

    # merge the stew config into the aggregated config since it is allowed to override presets
    merge(aggregated_config, stew_config)

    # separate the ci config since it's a different object
    ci_config = aggregated_config.pop("ci", {})

    io.write_line("\nStew config:", verbosity=Verbosity.VERBOSE)
    io.write_line(pformat(aggregated_config), verbosity=Verbosity.VERBOSE)
    io.write_line("\nCI Config:", verbosity=Verbosity.VERBOSE)
    io.write_line(pformat(ci_config), verbosity=Verbosity.VERBOSE)

    return aggregated_config, ci_config


def load_preset(module: ModuleType, preset_name: str) -> dict:
    preset_fn: Optional[Callable] = None

    if hasattr(module, preset_name):
        preset_fn = getattr(module, preset_name)
    else:
        preset_name = preset_name.replace("-", "_")
        if hasattr(module, preset_name):
            preset_fn = getattr(module, preset_name)

    if not preset_fn:
        raise ExitWithFailure() from ValueError(f"Preset not found: {preset_name}")
    if not callable(preset_fn):
        raise ExitWithFailure() from ValueError(
            f"Preset is not callable: {preset_name} -> {type(preset_fn)}"
        )
    preset = preset_fn()
    if not isinstance(preset, dict):
        raise ExitWithFailure() from ValueError(
            f"Preset function must return a dict: {preset_name} -> {type(preset)}"
        )
    return preset
