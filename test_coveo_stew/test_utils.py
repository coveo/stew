from coveo_testing.parametrize import parametrize

from coveo_stew.utils import strip_ansi


@parametrize(
    "text, expected",
    (
        ("plain text", "plain text"),
        ("", ""),
        ("\x1b[31mred\x1b[0m", "red"),
        ("\x1b[1;32mbold green\x1b[0m", "bold green"),
        ("\x1b[0m", ""),
        ("before \x1b[33myellow\x1b[0m after", "before yellow after"),
        ("\x1b(Bsome text", "some text"),  # VT100 character set sequence
    ),
)
def test_strip_ansi(text: str, expected: str) -> None:
    assert strip_ansi(text) == expected
