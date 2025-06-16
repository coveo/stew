# Stew Configuration Guide

This guide provides detailed information about configuring `coveo-stew` through your `pyproject.toml` file.

## Basic Configuration

All configuration for stew is done within the `pyproject.toml` file under the `[tool.stew]` section:

```toml
[tool.stew]
build-without-hashes = false
pydev = false
build-dependencies = { }
extras = []
all-extras = false
quick = { }
```

### Core Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `build-without-hashes` | `false` | When `true`, hashes are disabled when calling `pip` to download dependencies during `stew build`. Use this if you encounter issues with missing hashes in the poetry.lock file. |
| `pydev` | `false` | When `true`, marks this project as a development environment for multiple projects. See the [multiple-libraries](README_MULTIPLE_LIBRARIES.md) guide. |
| `build-dependencies` | `{}` | Additional dependencies to install during `stew build`. Format is the same as poetry dependencies: `name = "version"` or `name = { version = "version", ... }`. |
| `extras` | `[]` | A list of extras to install during `stew build` and `stew ci`. Can be overridden at runtime with `--extra`. |
| `all-extras` | `false` | When `true`, all extras will be installed during `stew build` and `stew ci`. Overrides the `extras` list. Can be specified at runtime with `--all-extras` and `--no-extras`. |
| `quick` | `{}` | Controls which checks are skipped when calling `stew ci --quick`. |
| `presets` | `[]` | A list of presets to use when working with this project. Presets can be used instead of configuring the `pyproject.toml` file. |  


### Presets Configuration

You can use presets to reduce the redundancy of the configuration between projects:

1. Presets are applied in the order they are defined in the `pyproject.toml` file.
2. The default preset is always loaded first.
3. Anything specified in the `pyproject.toml` file overrides what presets may have configured.

We recommend using this syntax to configure a list of presets:

```toml
[tool.stew]
presets = [ "clean-imports", "ruff" ]
```

The available builtin presets can be listed by typing `poetry stew presets` in the terminal.

User-defined presets are not supported at the moment [(planned)](https://github.com/coveo/stew/issues/105).


### Quick Mode Configuration

The `quick` option controls which checks are run or skipped when using the `--quick` flag with `stew ci`. It accepts
either a `check` or `skip` key followed by a list of runners:

```toml
[tool.stew]
# Skip these checks in quick mode
quick.skip = ["poetry-check", "check-outdated", "poetry-build", "pytest"]

# Or, only run these checks in quick mode
quick.check = ["mypy", "black"]
```

## CI Configuration

Configure which CI tools to run under the `[tool.stew.ci]` section:

```toml
[tool.stew.ci]
mypy = true
pytest = false
black = false
poetry-check = true
check-outdated = true
offline-build = false
```

### Built-in Runners Configuration

Each built-in runner can be configured with specific options:

#### mypy configuration

```toml
[tool.stew.ci]
# Disable stew's strict mypy config (let mypy find its config)
mypy.set-config = false

# Use a specific config (path relative to pyproject.toml's folder)
mypy.set-config = "mypy.ini"
```

#### pytest configuration

```toml
[tool.stew.ci.pytest]
# Configure the markers to test (i.e.: `-m`)
marker-expression = 'not docker_tests'

# Disable the doctests
doctest-modules = false
```

#### black configuration

Black can be configured using its own section:

```toml
[tool.black]
line-length = 100
```

## Custom Runners

Define custom runners in the `[tool.stew.ci.custom-runners]` section. See [README_RUNNERS.md](README_RUNNERS.md) for
detailed information.
