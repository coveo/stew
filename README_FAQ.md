# FAQ and Troubleshooting Guide

This document addresses common questions and issues you might encounter when using coveo-stew.

## General Questions

### What's the difference between `coveo-stew` v3.x and v4.x?

Version 4.0 restructured coveo-stew as a Poetry plugin instead of a standalone CLI tool. This change provides better integration with Poetry and ensures compatibility with newer Poetry versions. The main difference is that all commands now need to be prefixed with `poetry`:

- `stew ci` → `poetry stew ci`
- `stew build` → `poetry stew build`

### Can I use coveo-stew with older Python versions?

coveo-stew requires Python 3.9+ to run, but it can manage projects that target older Python versions. Poetry must be installed with Python 3.9+, but your projects can specify older versions in their dependencies.

### How do I know which version of coveo-stew I'm using?

You can check your installed version with:

```bash
poetry self show plugins
```

Or you can use the builtin command, especially if you need a machine-readable output:

```bash
poetry stew version
```

## Installation Issues

### Poetry can't find the stew plugin

If you get an error like "No such command", make sure:

1. coveo-stew is installed correctly: `poetry self show plugins` should list it
2. You're using Poetry 2.0 or higher: `poetry --version`
3. You've installed it correctly for your Poetry installation method

### pip install fails with dependency conflicts

When installing with pip directly, you might encounter dependency conflicts. Using `pipx` is recommended as it creates isolated environments for each tool:

```bash
pipx install poetry
pipx inject poetry coveo-stew
```

## Command Issues

### `poetry stew ci` fails with "command not found" errors

This typically happens when a tool (like mypy or black) isn't installed. Ensure these tools are:

1. Added to your project's dev dependencies:
   ```toml
   [tool.poetry.group.dev.dependencies]
   mypy = "*"
   black = "*"
   ```
2. Installed in your project's environment: `poetry install`

### `poetry stew build` fails with missing hashes

If you see an error related to missing hashes, add this to your `pyproject.toml`:

```toml
[tool.stew]
build-without-hashes = true
```

### `poetry stew pull-dev-requirements` doesn't update all dependencies

In v4.0, this command aggregates all non-optional groups from dependencies, not just the "dev" group. Make sure your dependency groups aren't marked as optional if you want them included.

## Multiple Projects Issues

### Can't find local projects in multi-project setup

Make sure:

1. Your root project has `pydev = true` in `[tool.stew]`
2. Each local project is referenced with `path` in the root project:
   ```toml
   [tool.poetry.dependencies]
   local-project = { path = "./local-project/", develop = true }
   ```
3. Each project has a valid `pyproject.toml` and follows the structure described in [README_MULTIPLE_LIBRARIES.md](./README_MULTIPLE_LIBRARIES.md)

### Changes in local libraries aren't reflected when running

Make sure the local dependencies are installed with `develop = true` in the path reference:

```toml
[tool.poetry.dependencies]
my-lib = { path = "./my-lib/", develop = true }
```

## CI/CD Integration

### GitHub Actions workflow fails with "stew command not found"

If you're using the GitHub Actions workflow and getting errors, make sure you're using the updated plugin action:

```yaml
- uses: coveo/stew/plugin@main
```

### How to use coveo-stew in CI pipelines other than GitHub

For other CI systems, install Poetry and coveo-stew as part of your pipeline:

```bash
# For pipelines with Python pre-installed
pipx install poetry
pipx inject poetry coveo-stew

# Then run stew commands
poetry stew ci
```

## Offline Distribution

### How to create a deployable package with all dependencies

To create an offline-installable package:

1. Run `poetry stew build --target <folder>` to create a directory with all needed wheel files
2. This folder can be copied to any system and installed with:
   ```bash
   pip install --no-index --find-links <folder> your-package-name
   ```

### Best practices for deployable packages

1. Always use the same Python version and OS for building as you'll use for deployment
2. Consider using the `--python` option to target a specific Python interpreter
3. Keep your build folder clean to avoid mixing versions
4. Add `build-without-hashes = true` if you encounter hash verification errors

## Advanced Usage

### How to integrate custom tools not covered by built-in runners

Create a custom runner in your `pyproject.toml`:

```toml
[tool.stew.ci.custom-runners]
my-tool = { check-args = ["--check", "--path", "."] }
```

### How to debug issues in stew commands

Run stew commands with verbose Poetry output:

```bash
poetry -vvv stew ci
```

This will show more detailed information about what's happening behind the scenes.

## Still Having Problems?

If you encounter issues not covered here:

1. Check if there are any open issues on the [GitHub repository](https://github.com/coveo/stew/issues)
2. Make sure you're using the latest version of coveo-stew and Poetry
3. Open a new issue with details about your environment and a minimal reproducible example
