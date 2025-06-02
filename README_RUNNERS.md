# CI Runners Guide

This guide details the CI runners available in coveo-stew and how to configure custom runners.

## Built-in Runners

By default, `poetry stew ci` includes several built-in runners that can be enabled or disabled in your `pyproject.toml` file:

```toml
[tool.stew.ci]
mypy = true                 # Type checking
pytest = false              # Run tests
black = false               # Code formatting
poetry-check = true         # Validate poetry config
check-outdated = true       # Check for outdated files
offline-build = false       # Test offline build capability
```

### mypy Runner

Runs mypy type checking on your codebase with strict checking enabled by default.

```toml
[tool.stew.ci]
# Enable with default settings
mypy = true

# Disable strict config (use project's mypy.ini/setup.cfg)
mypy = { set-config = false }

# Use a specific config file
mypy = { set-config = "mypy.ini" }

# Specify paths to type-check (overriding automatic detection)
mypy = { check-paths = ["src", "tools"] }

# Specify a single path
mypy = { check-paths = "src" }

# Exclude specific paths from type-checking
mypy = { skip-paths = ["tests", "examples"] }
```

By default, the mypy runner automatically detects and type-checks folders containing a `py.typed` file (as per [PEP 561](https://www.python.org/dev/peps/pep-0561/)).

Options exist to control which paths are type-checked:

1. **Explicit inclusion**: Use `check-paths` to specify exactly which paths should be type-checked, overriding automatic detection entirely.
2. **Selective exclusion**: Use `skip-paths` to exclude specific paths from automatic detection.

Note that `check-paths` and `skip-paths` are mutually exclusive.

### pytest Runner

Runs your test suite using pytest.

```toml
[tool.stew.ci]
# Enable with default settings
pytest = true

# Configure markers
pytest = { marker-expression = "not slow" }

# Disable doctest
pytest = { doctest-modules = false }

# Multiple configurations
pytest = { 
  marker-expression = "not slow", 
  doctest-modules = false,
  junit-report = "custom-report.xml"
}
```

### black Runner

Checks your code against the black formatter.

```toml
[tool.stew.ci]
# Enable with default settings
black = true
```

When run with `--fix`, black will auto-format your code if it finds styling issues.

### poetry-check Runner

Validates your poetry configuration.

```toml
[tool.stew.ci]
# Enable with default settings
poetry-check = true
```

### check-outdated Runner

Checks for outdated files according to your project's dependency graph.

```toml
[tool.stew.ci]
# Enable with default settings
check-outdated = true
```

When run with `--fix`, it will update those files automatically.

### offline-build Runner

Tests whether your project can be built for offline distribution.

```toml
[tool.stew.ci]
# Enable with default settings
offline-build = true
```

## Custom Runners

You can define custom runners for any command-line tool. Custom runners are defined in the `[tool.stew.ci.custom-runners]` section:

```toml
[tool.stew.ci.custom-runners]
# Simplest form: just enable the runner with default settings
flake8 = true

# Specify command-line arguments
bandit = { check-args = ["--quiet", "--recursive", "."] }

# Runner with auto-fix capability
isort = { 
  check-args = ["--check", ".", "--profile", "black"],
  autofix-args = [".", "--profile", "black"]
}
```

### Custom Runner Options

| Option | Description                                                          |
|--------|----------------------------------------------------------------------|
| `check-args` | Arguments to pass to the runner when checking                        |
| `autofix-args` | Arguments to pass when fixing issues (used with `--fix` flag)        |
| `force-fix` | When `true`, run the fix command even if the check didn't fail       |
| `junit-report` | Path to write JUnit XML report (relative to project)                 |
| `report-file` | Path to write the plain text report (relative to project)            |
| `fail-level` | Minimum severity level to cause failure (`error`, `warning`, `info`) |
| `report-level` | Minimum level to report (`error`, `warning`, `info`, `debug`)        |

### Example: Adding pylint

```toml
[tool.stew.ci.custom-runners]
pylint = { 
  check-args = ["--rcfile=pylintrc", "--output-format=text", "your_package"],
  report-file = ".ci/pylint-report.txt",
  junit-report = ".ci/pylint-junit.xml"
}
```

### Example: Adding isort with auto-fixing

```toml
[tool.stew.ci.custom-runners.isort]
check-args = ["--check-only", "--profile", "black", "."]
autofix-args = ["--profile", "black", "."]
junit-report = ".ci/isort-junit.xml"
```

## Runtime Control

You can control which runners execute during a CI run using command-line flags:

```bash
# Run only specific runners
poetry stew ci --check mypy --check black

# Skip specific runners
poetry stew ci --skip pytest --skip black

# Enable auto-fixing
poetry stew ci --fix
```

The `--check` and `--skip` options can be repeated to specify multiple runners.
