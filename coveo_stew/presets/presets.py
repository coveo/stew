def default() -> dict:
    """This preset is automatically loaded by stew and defines the default configuration."""
    return {
        "build_without_hashes": False,
        "pydev": False,
        "build_dependencies": {},
        "extras": [],
        "all_extras": False,
        "quick": {},
        "ci": {
            "disabled": False,
            "mypy": True,
            "check_outdated": True,
            "poetry_check": True,
            "pytest": False,
            "offline_build": False,
            "black": False,
            "custom_runners": {},
        },
    }


def clean_imports(profile: str = "black") -> dict:
    """isort and autoflake work together to sort and clean imports"""
    autoflake_defaults = [
        "--recursive",
        "--remove-all-unused-imports",
        "--remove-unused-variables",
    ]

    isort_defaults = [f"--profile={profile}"]

    return {
        "ci": {
            "custom_runners": {
                "isort": {
                    "check-args": ["--check", ".", *isort_defaults],
                    "autofix-args": [".", *isort_defaults],
                },
                "autoflake": {
                    "check-args": ["--check", ".", *autoflake_defaults],
                    "autofix-args": ["--in-place", ".", *autoflake_defaults],
                },
            }
        }
    }


def ruff() -> dict:
    """
    Ruff is a fast linter and formatter for Python.

    This preset comes with three custom runners:
    - `ruff-format`: Runs ruff to check and fix formatting issues.
    - `ruff-isort`: Runs ruff check and fix import sorting issues.
    - `ruff-check`: Runs ruff to report typing issues.
    """
    ruff_defaults = {"executable": "ruff", "working-directory": "project"}

    return {
        "mypy": False,
        "black": False,
        "ci": {
            "custom_runners": {
                "ruff-check": {
                    **ruff_defaults,
                    "check-args": ["check", "."],
                },
                "ruff-format": {
                    **ruff_defaults,
                    "check-args": ["format", "--check", "."],
                    "autofix-args": ["format", "."],
                },
                "ruff-isort": {
                    **ruff_defaults,
                    "check-args": ["check", "--select", "I"],
                    "autofix-args": ["check", "--select", "I", "--fix"],
                },
            }
        },
    }
