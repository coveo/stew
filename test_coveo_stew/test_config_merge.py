import pytest

from coveo_stew.config import merge


@pytest.mark.parametrize(
    "a, b, expected",
    [
        # Simple merge case
        ({"key1": "value1"}, {"key2": "value2"}, {"key1": "value1", "key2": "value2"}),
        # Nested dictionary merge
        (
            {"outer": {"inner1": "value1"}},
            {"outer": {"inner2": "value2"}},
            {"outer": {"inner1": "value1", "inner2": "value2"}},
        ),
        # Complex nested dictionary merge
        (
            {"level1": {"level2": {"level3a": "value1"}}},
            {"level1": {"level2": {"level3b": "value2"}}},
            {"level1": {"level2": {"level3a": "value1", "level3b": "value2"}}},
        ),
        # Conflict cases where value from b overwrites value from a
        ({"key": "value1"}, {"key": "value2"}, {"key": "value2"}),
        (
            {"outer": {"inner": "value1"}},
            {"outer": {"inner": "value2"}},
            {"outer": {"inner": "value2"}},
        ),
        # Empty dictionaries
        ({}, {}, {}),
        ({"key": "value"}, {}, {"key": "value"}),
        ({}, {"key": "value"}, {"key": "value"}),
        # List merging tests
        ({"list_key": [1, 2]}, {"list_key": [3, 4]}, {"list_key": [1, 2, 3, 4]}),
        ({"list_key": []}, {"list_key": [1, 2]}, {"list_key": [1, 2]}),
        ({"list_key": [1, 2]}, {"list_key": []}, {"list_key": [1, 2]}),
        # Nested list merging
        (
            {"outer": {"list_key": [1, 2]}},
            {"outer": {"list_key": [3, 4]}},
            {"outer": {"list_key": [1, 2, 3, 4]}},
        ),
        # Mixed type testing - lists and dictionaries
        (
            {"dict_key": {"a": 1}, "list_key": [1, 2]},
            {"dict_key": {"b": 2}, "list_key": [3, 4]},
            {"dict_key": {"a": 1, "b": 2}, "list_key": [1, 2, 3, 4]},
        ),
        # Key normalization tests (treating underscores and hyphens as equivalent)
        (
            {"custom_runners": [1, 2]},
            {"custom-runners": [3, 4]},
            {"custom_runners": [1, 2, 3, 4]},
        ),
        (
            {"parent": {"child_key": "value1"}},
            {"parent": {"child-key": "value2"}},
            {"parent": {"child_key": "value2"}},
        ),
        (
            {"with-hyphens": {"nested-key": "value1"}},
            {"with_hyphens": {"nested_key": "value2"}},
            {"with-hyphens": {"nested-key": "value2"}},
        ),
        (
            {"a_b_c": {"x_y_z": "value1"}},
            {"a-b-c": {"x-y-z": "value2"}},
            {"a_b_c": {"x_y_z": "value2"}},
        ),
    ],
    ids=[
        "simple_dict",
        "nested_dict",
        "complex_nested_dict",
        "conflict",
        "nested_conflict",
        "empty_dicts",
        "first_dict_with_values",
        "second_dict_with_values",
        "merge_lists",
        "merge_empty_and_populated_list",
        "merge_populated_and_empty_list",
        "nested_list_merge",
        "mixed_dict_and_list_merge",
        "normalize_underscore_hyphen_in_list_keys",
        "normalize_keys_in_nested_dict",
        "normalize_keys_with_hyphens_first",
        "normalize_multiple_underscores_hyphens",
    ],
)
def test_merge_dictionaries(a: dict, b: dict, expected: dict) -> None:
    merge(a, b)
    assert a == expected
