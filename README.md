# coveo-stew

![Version](https://img.shields.io/pypi/v/coveo-stew)
![License](https://img.shields.io/github/license/coveo/stew)

coveo-stew is a Poetry plugin that delivers simple CI/CD tools for python using [poetry](https://python-poetry.org) as its backend.

> [!IMPORTANT]
> **Version 4.0 Breaking Changes**
> 
> Version 4.0 is a major breaking change as `coveo-stew` was rewritten as a Poetry plugin
> which required some changes to the command line interface.
> 
> If you're upgrading from a previous version, please refer to the [upgrade guide](./README_UPGRADE.md).

## Features

### CI tools
- Config-free pytest, mypy and black runners
- Add your own linters and tools
- JUnit report generation
- GitHub Action that runs all your CI tools

Similar to: tox

### CD tools
- GitHub Action for Continuous Delivery (CD) (publish to pypi)
- Automated "patch" version bumps (requires a `pypi` server)
- Can download locked dependencies into a folder, for offline distribution

Similar to: poetry, flit, pbr, setuptools

### Multiple projects
- Support for several isolated poetry projects in one GitHub repository
- Support for local path references
- A "one ring to rule them all" virtual environment that includes all subprojects within the repository
- Batch operations

Similar to: nothing! it's unique! 😎

## Prerequisites

- Poetry 2.0 or higher
- Poetry must be installed with Python 3.9 or higher

## Installation

`coveo-stew` can be installed either as a Poetry plugin or as a standalone CLI tool.

### As a Poetry plugin (recommended for CI servers)

Starting from coveo-stew version 4.0, you can install stew as a Poetry plugin.

We recommend this approach for CI servers: it's easier to inject a plugin into poetry than to install a new CLI tool
into the path.
Also, since poetry and stew share some common dependencies, it can translate into faster setups.

Installation depends on how you installed Poetry:

#### Using pipx

```shell
pipx install poetry
pipx inject poetry "coveo-stew>=4"
```

See the [poetry documentation](https://python-poetry.org/docs/plugins/#using-plugins) for more information and alternative installation methods.

### As a standalone CLI tool

The main appeal of this approach is that it's shorter to type, making it a popular option for local development.

In order to install stew as a standalone CLI tool, we recommend using `pipx`:

```shell
pipx install coveo-stew
```

> Note: Having both the plugin and the CLI won't cause issues.
 

## GitHub Action

This action installs Python, Poetry, and Stew, then runs "stew ci" on your Python project.

```yml
jobs:
  stew-ci:
    runs-on: ubuntu-latest
    steps:
      - uses: coveo/stew@main
        with:
          python-version: "3.10"
          project-name: your-project-name
```

See additional options and documentation in [the action file](./action.yml).

## Repository Structure

Please read these guides to learn how to organize your repository for maximum compatibility:

- [For a single library](README_SINGLE_LIBRARY.md)
- [For multiple libraries](README_MULTIPLE_LIBRARIES.md)

## Commands

### General command usage

Calling coveo-stew will depend on how you installed it:

1. As a Poetry plugin:

    ```bash
    poetry stew <command> [options]
    ```

2. As a standalone CLI tool:

    ```bash
    stew <command> [options]
    ```

Both interfaces provide identical functionality. You can choose whichever approach you prefer based on your workflow.

Unless a project name is specified, commands will operate on all projects in a git repository:

```bash
# Perform a command on all projects
poetry stew <command>
# Or using the standalone CLI
stew <command>

# Get help about a specific command
poetry stew <command> --help
# Or using the standalone CLI
stew <command> --help
```

Some commands allow specifying a project name:

```bash
# Run on all projects with <project-name> in their name (partial, case-insensitive)
poetry stew <command> <project-name>
# Or using the standalone CLI
stew <command> <project-name>

# Disable partial project name matching
poetry stew <command> <project-name> --exact-match
# Or using the standalone CLI
stew <command> <project-name> --exact-match

# Only consider the project at this location
poetry stew <command> .<path>
# Or using the standalone CLI
stew <command> .<path>
```

The remainder of the documentation will use `stew <command>` for brevity. Simply prefix with `poetry` if you installed it as a plugin.

## Main Commands

### `stew ci`

Runs all CI tools on one or multiple projects. Errors will show in the console, and JUnit XML reports will be generated inside the `.ci` folder.

Without configuration, this command will run:
- mypy (using opinionated, strict rules)
- poetry check
- stew check-outdated

Options:
- `--fix`: Reformat code if `black` fails
- `--check <runner>`: Launch only that runner (can be repeated)
- `--skip <runner>`: Skip that runner (takes precedence over `--check`, can be repeated)
- `--quick`: Skip running `poetry install --remove-untracked` before running the checks
- `--extra <extra>`: Install the specified extra(s) for this run (can be repeated)
- `--all-extras`: Install all extras for this run
- `--no-extras`: Don't install any extras for this run

### `stew build`

Store the project and its **locked dependencies** to disk for offline installation:

```bash
stew build --target <folder>
```

The folder can later be installed offline with:

```bash
pip install --no-index --find-links <folder> <project-name>
```

Options:
- `--target`: Specifies where wheels should be downloaded
- `--python`: Target a different Python version/environment

**Important**: Make sure your target folder is clean before building.

### Other useful commands

- `stew check-outdated`: Check for or update out-of-date files
- `stew pull-dev-requirements`: Update dev requirements in a `pydev` project
- `stew bump`: Run `poetry lock` on all projects
- `stew refresh`: Run `poetry install` on all projects
- `stew fresh-eggs`: Clear `.egg-info` folders (useful when changing `[tool.poetry.scripts]`)
- `stew locate <project>`: Return the path to a project

## Configuration

Configuration is done through the `pyproject.toml` file:

```toml
[tool.stew]
build-without-hashes = false  # Disable hashes when calling pip during stew build
pydev = false                 # Enable pydev mode (see multiple-libraries guide)
build-dependencies = {}       # Additional dependencies for stew build
extras = []                   # Extras to install during stew build and stew ci
all-extras = false            # Install all extras during stew build and stew ci
quick = {}                    # Controls which checks are skipped with --quick

[tool.stew.ci]
mypy = true
pytest = false
black = false
poetry-check = true
check-outdated = true
offline-build = false

# Custom runners
[tool.stew.ci.custom-runners]
flake8 = true
bandit.check-args = ["--quiet", "--recursive", "."]

[tool.stew.ci.custom-runners.isort]
check-args = ["--check", ".", "--profile", "black"]
autofix-args = [".", "--profile", "black"]
```

See the full documentation for [stew configuration](README_CONFIGURATION.md) and [CI runners](README_RUNNERS.md).

## FAQ and Troubleshooting

See our [FAQ and Troubleshooting guide](README_FAQ.md) for solutions to common issues and best practices.
