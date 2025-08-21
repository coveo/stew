# FAQ and Troubleshooting Guide

This document addresses common questions and issues you might encounter when using coveo-stew.

## General Questions

### Are the plugin and CLI versions of coveo-stew the same?

Yes, both the plugin and CLI versions of coveo-stew are functionally equivalent.

There is one difference, which is the verbosity switch:
- In the CLI version, use either `--verbose` or `-v` to enable verbose output.
- In the plugin version, use `-v` to enable verbose output.

Note: Stew only has one verbosity level (-v). Using `-vv` or `-vvv` will only increase poetry's verbosity.


### Can I use coveo-stew with older Python versions?

coveo-stew requires Python 3.9+ to run, but it can manage projects that target older Python versions. Poetry must be installed with Python 3.9+, but your projects can specify older versions in their dependencies.

### How do I know which version of coveo-stew I'm using?

Plugin users may check the installed version with:

```bash
poetry self show plugins
```

If you need a machine-readable output or are using the CLI:

```bash
stew version  # cli
poetry stew version  # plugin
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

### `stew ci` fails with "command not found" errors

This typically happens when a tool (like mypy or black) isn't installed. Ensure these tools are:

1. Added to your project's dev dependencies:
   ```toml
   [tool.poetry.group.dev.dependencies]
   mypy = "*"
   black = "*"
   ```
2. Installed in your project's environment: `poetry install`

### `stew build` fails with missing hashes

If you see an error related to missing hashes, add this to your `pyproject.toml`:

```toml
[tool.stew]
build-without-hashes = true
```

### `stew pull-dev-requirements` doesn't update all dependencies

In v4.0, this command aggregates all non-optional groups from dependencies, not just the "dev" group. Make sure your dependency groups aren't marked as optional if you want them included.

### Cancelling stew with Ctrl+C prints a traceback

This is a known issue with asyncio, particularly on Windows. 
It happens because the asyncio event loop doesn't handle cancellation gracefully.

You can safely ignore the traceback, as it doesn't affect the functionality of stew.

e.g.:

```bash
Aborted!
Exception ignored in: <function BaseSubprocessTransport.__del__ at 0x0000020DEC7ECD60>
Traceback (most recent call last):
  File "C:\py\3.12\Lib\asyncio\base_subprocess.py", line 126, in __del__
    self.close()
  File "C:\py\3.12\Lib\asyncio\base_subprocess.py", line 104, in close
    proto.pipe.close()
  File "C:\py\3.12\Lib\asyncio\proactor_events.py", line 109, in close
    self._loop.call_soon(self._call_connection_lost, None)
  File "C:\py\3.12\Lib\asyncio\base_events.py", line 795, in call_soon
    self._check_closed()
  File "C:\py\3.12\Lib\asyncio\base_events.py", line 541, in _check_closed
    raise RuntimeError('Event loop is closed')
RuntimeError: Event loop is closed
```

```bash
Exception ignored in: <function _ProactorBasePipeTransport.__del__ at 0x0000020DEC7EE520>
Traceback (most recent call last):
  File "C:\py\3.12\Lib\asyncio\proactor_events.py", line 116, in __del__
    _warn(f"unclosed transport {self!r}", ResourceWarning, source=self)
                               ^^^^^^^^
  File "C:\py\3.12\Lib\asyncio\proactor_events.py", line 80, in __repr__
    info.append(f'fd={self._sock.fileno()}')
                      ^^^^^^^^^^^^^^^^^^^
  File "C:\py\3.12\Lib\asyncio\windows_utils.py", line 102, in fileno
    raise ValueError("I/O operation on closed pipe")
ValueError: I/O operation on closed pipe
```

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

### How to use coveo-stew in CI pipelines other than GitHub

For other CI systems, install Poetry and coveo-stew as part of your pipeline:

```bash
# For pipelines with Python pre-installed
pipx install poetry
pipx inject poetry coveo-stew

# Then run stew commands through `poetry`
poetry stew ci
```

## Offline Distribution

### How to create a deployable package with all dependencies

To create an offline-installable package:

1. Run `stew build --target <folder>` to create a directory with all needed wheel files
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
my-tool.check-args = ["--check", "--path", "."]
```

_(Alternative toml syntax)_:

```toml
[tool.stew.ci.custom-runners.my-tool]
check-args = ["--check", "--path", "."]
```

Then run it with:
```
stew ci --check my-tool  # run only my-tool
stew ci  # run everything, including my-tool
```

### How to debug issues in stew commands

Run stew commands with verbose output:

```bash
poetry -vv stew ci  # plugin
stew ci --verbose  # cli
```

This will show more detailed information about what's happening behind the scenes.

## Still Having Problems?

If you encounter issues not covered here:

1. Check if there are any open issues on the [GitHub repository](https://github.com/coveo/stew/issues)
2. Make sure you're using the latest version of coveo-stew and Poetry
3. Open a new issue with details about your environment and a minimal reproducible example
