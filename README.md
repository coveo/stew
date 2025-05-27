# coveo-stew

![Version](https://img.shields.io/pypi/v/coveo-stew)
![License](https://img.shields.io/github/license/coveo/stew)

coveo-stew is a Poetry plugin that delivers simple CI/CD tools for python using [poetry](https://python-poetry.org) as its backend.

> [!IMPORTANT]
> **Version 4.0 Breaking Changes**
> 
> Version 4.0 is a major breaking change as `coveo-stew` was rewritten as a Poetry plugin instead of a standalone CLI tool.
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

- Poetry 1.8 or higher
- Poetry must be installed with Python 3.9 or higher

## Installation

`coveo-stew` is a poetry plugin. Installation depends on how you installed poetry.

### Using pipx (recommended)

```shell
pipx install poetry
pipx inject poetry coveo-stew
```

See the [poetry documentation](https://python-poetry.org/docs/plugins/#using-plugins) for more information and alternative installation methods.

## GitHub Action

This action installs Python, Poetry, and Stew, then runs "poetry stew ci" on your Python project.

```yml
jobs:
  stew-ci:
    runs-on: ubuntu-latest
    steps:
      - uses: coveo/stew/plugin@main
        with:
          python-version: "3.10"
          project-name: your-project-name
```

See additional options and documentation in [the action file](plugin/action.yml).

## Repository Structure

Please read these guides to learn how to organize your repository for maximum compatibility:

- [For a single library](README_SINGLE_LIBRARY.md)
- [For multiple libraries](README_MULTIPLE_LIBRARIES.md)

## Commands

### General command usage

All stew commands are now used as Poetry plugins:

```bash
poetry stew <command> [options]
```

Unless a project name is specified, commands will operate on all projects in a git repository:

```bash
# Perform a command on all projects
poetry stew <command>

# Get help about a specific command
poetry stew <command> --help
```

Some commands allow specifying a project name:

```bash
# Run on all projects with <project-name> in their name (partial, case-insensitive)
poetry stew <command> <project-name>

# Disable partial project name matching
poetry stew <command> <project-name> --exact-match

# Only consider the project at this location
poetry stew <command> .<path>
```

## Main Commands

### `poetry stew ci`

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

### `poetry stew build`

Store the project and its **locked dependencies** to disk for offline installation:

```bash
poetry stew build --target <folder>
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

- `poetry stew check-outdated` / `poetry stew fix-outdated`: Check for or update out-of-date files
- `poetry stew pull-dev-requirements`: Update dev requirements in a `pydev` project
- `poetry stew bump`: Run `poetry lock` on all projects
- `poetry stew refresh`: Run `poetry install` on all projects
- `poetry stew fresh-eggs`: Clear `.egg-info` folders (useful when changing `[tool.poetry.scripts]`)
- `poetry stew locate <project>`: Return the path to a project

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
bandit = { check-args = ["--quiet", "--recursive", "."] }

[tool.stew.ci.custom-runners.isort]
check-args = ["--check", ".", "--profile", "black"]
autofix-args = [".", "--profile", "black"]
```

See the full documentation for [stew configuration](README_CONFIGURATION.md) and [CI runners](README_RUNNERS.md).

## FAQ and Troubleshooting

See our [FAQ and Troubleshooting guide](README_FAQ.md) for solutions to common issues and best practices.
