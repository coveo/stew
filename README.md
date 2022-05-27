# coveo-stew

coveo-stew delivers a complete Continuous Integration (CI) and Continuous Delivery (CD) solution
using [poetry](https://python-poetry.org) as its backend.


# Features

## CI tools
- Builtin, config-free pytest, mypy and black runners
- Add your own linters and tools
- JUnit report generation
- GitHub Action that runs all your CI tools

Similar to: tox

## CD tools
- GitHub Action for Continuous Delivery (CD) (publish to pypi)
- Automated "patch" version bumps (requires a `pypi` server)
- Can download locked dependencies into a folder, for offline distribution

Similar to: poetry, flit, pbr, setuptools

## Multiple projects
- Support for several isolated poetry projects in one GitHub repository
- Support for local path references
- A "one ring to rule them all" virtual environment that includes all subprojects within the repository
- Batch operations
- Note: Single projects are also supported! 😅

Similar to: nothing! it's unique! 😎 


# Installation

Just like poetry, `stew` is a CLI tool that you install in your system.

It is recommended to install using [pipx](https://github.com/pipxproject/pipx) in order to isolate this into a nice little space:

```
pip install pipx --user
pipx install coveo-stew
```

If you don't use pipx, make sure to isolate the installation into a virtual environment, otherwise it may interfere with an existing poetry installation.


# Repository Structure

Please read these guides in order to learn how to organize your repository for maximum compatibility:

- [For a single library](README_SINGLE_LIBRARY.md)
- [For multiple libraries](README_MULTIPLE_LIBRARIES.md)


# Commands

## General command usage

Unless a project name is specified, most commands will operate on all projects in a git repository based on the current working folder:

- `stew <command>`
    - Perform a command on all projects
- `stew <command> --help`
    - Obtain help about a particular command
- `stew <command> <project-name>`
    - Perform the command on all projects with `<project-name>` in their name (partial match)
- `stew <command> <project-name> --exact-match`
    - Disable partial project name matching

The main commands are explained below.


## `stew ci`

The main show; it runs all CI tools on one or multiple projects.

Errors will show in the console, and junit xml reports will be generated inside the `.ci` folder.

Without configuration, this command will run the following checks:

- mypy (using opinionated, strict rules)
- poetry check
- stew check-outdated

Options:

- `--fix` will reformat the code if `black` fails. Additional fix routines may be added in the future.
- `--check <runner>` will launch only that runner. This option can be repeated.
- `--quick` skips running `poetry install --remove-untracked` before running the checks.


## `stew build`

Store the project and its **locked dependencies** to disk, so it can be installed without contacting a `pypi` server.

Optimally used to create truly repeatable builds and workflows (e.g.: containerized images, cloud storage, etc).

The folder can later be installed offline with `pip install --no-index --find-links <folder> <project-name>`.


Options:

- `--directory` specifies where the wheels should be downloaded.
- `--python` may be used to target a different python. It's important to use the same python version, architecture and OS than the target system.

**Make sure your target `<folder>` is clean**: Keep in mind that `pip` will still use the `pyproject.toml` constraints when installing, not `poetry.lock`. 
The locked version system works when the locked version is the only thing that `pip` can find in the `<folder>`.


## `stew check-outdated` and `stew fix-outdated` 

Checks for out-of-date files or automatically update them.

Summary of actions:
- `poetry lock` if `pyproject.toml` changed but not the `poetry.lock`
- `stew pull-dev-requirements` if a pydev project's dev-requirements are out of sync


## `stew bump`

Calls `poetry lock` on all projects.


## `stew refresh`

Calls `poetry install` on all projects.


## `stew fresh-eggs`

Clears the `.egg-info` folder from your projects. Usually followed by a `poetry install` or a `stew refresh`.

Use this if you change a `[tool.poetry.scripts]` section, else the changes will not be honored.


## `stew locate <project>`

Returns the path to a project:

```
$ stew locate coveo-stew
/home/jonapich/code/stew/coveo-stew
```

# Configuration

Configuration is done through each `pyproject.toml` file; default values are shown:

```
[tool.stew.ci]
mypy = true
pytest = false
black = false
poetry-check = true
check-outdated = true
offline-build = false
```

You don't have to include the `[tool.stew.ci]` section at all if these defaults suit you!


## Builtin Runners

Even though `coveo-stew` provides builtin `mypy` and `black`, we strongly suggest pinning them to your
`pyproject.toml` file in the `[tool.poetry.dev-dependencies]` section.

This way, mypy won't surprise you with new failures when they release new versions! 😎

Note: You can override and customize most runners by [rewriting them as custom runners.](#custom-runners)

### mypy

A strict mypy configuration is provided. 

You can provide your own mypy configuration, but you'll have to specify the `set-config` option: 

```
[tool.stew.ci]

# disable stew's strict mypy config (i.e.: let mypy find its config)
mypy = { set-config = False } 

# use a specific config (path relative to `pyproject.toml`'s folder)
mypy = { set-config = "mypy.ini" }
```

See https://mypy.readthedocs.io/en/stable/config_file.html#using-a-pyproject-toml

### pytest

Pytest is configured to run with `--doctest-modules --tb=short --durations=5` as well as JUnit report generation.

Some additional options are available:

```
[tool.stew.ci]

# configure the markers to test (i.e.: `-m`)
pytest = { marker-expression = 'not docker_tests' }

# disable the doctests
pytest = { doctest-modules = False }
```

Note: `pytest` is not bundled with `coveo-stew` at all! Make sure you add it to your project dependencies.


### black

Black supports the `pyproject.toml` file natively:

```
[tool.black]
line-length = 100
```

Ref: [black documentation](https://black.readthedocs.io/en/stable/usage_and_configuration/the_basics.html#configuration-via-a-file)


### poetry-check

Runs `poetry check` on each project.


### check-outdated

Runs `stew check-outdated`.

Note: This runner cannot be overridden, but it can be disabled.


### offline-build

Runs `stew build` to a temporary folder and ensures that pip is able to reinstall everything from there.

Note: This runner cannot be overridden, but it can be disabled.


## Custom Runners

You can add your own runners to `stew ci`. 
You can also redefine a builtin runner completely.

In this example, we create runners for flake8, bandit and isort. We also redefine the pytest runner:


```
[tool.stew.ci.custom-runners]
flake8 = true
bandit = { check-args = ["--quiet", "--recursive", "."] }

# some may prefer this toml syntax:
[tool.stew.ci.custom-runners.isort]
check-args = ["--check", ".", "--profile black"]
autofix-args = [".", "--profile black"]

[tool.stew.ci.custom-runners.pytest] 
check-args = ["--tb=long", "--junitxml=.ci/pytest-results.xml"]
```

When a builtin runner such as pytest is redefined as a custom runner, you must provide all the arguments.
In this case, not passing `--junitxml` would mean that we lose the report that used to be in the `.ci/` directory. 


### Options

The following options are supported for custom runners:

- name: You can specify the module name if it differs from the name of the tool.
  - Important: Runners are called through `python -m <name>`, not through the shell! 
- check-args: The arguments to invoke the check.
- autofix-args: The arguments to invoke the autofix. Provide the empty string "" in order to run without arguments.
- check-failed-exit-codes: A list of ints denoting the exit codes to consider "failed" (anything else will be "error"). 0 is always a success. default is `[1]`.
- create-generic-report: Whether to create a generic pass/fail JUnit report for this check.
- working-directory: The default is "project" which corresponds to the project's `pyproject.toml` file. You can change it to "repository" in order to run from the root.

The `args` and `check-args` can be:

- A string
  - Such as a single argument "--check"
  - Such as a path "."
  - Such as an option "--profile black"
  - But NOT as a combo of the above: "--check . --profile black" will most likely not work.

- A list of string:
  - Any combination of the "string" rules explained above.


# FAQ, Tips and Tricks

## constraints vs locks - where do they apply?

When you call `poetry install`, you end up installing packages based on the `poetry.lock` file.
The resulting packages will always be the same, no matter what.
This is the dev scenario.

When you call `pip install`, you are installing packages based on the constraints placed in a `pyproject.toml` or a `setup.py` file.
Unless the constraints are hard pinned versions, the resulting packages are not guaranteed and will depend on the point in time when the installation is performed, among other factors.
This is the shared library scenario.

When you use poetry, you cover the two scenarios above.

The third scenario is the private business use case: you want to freeze your dependencies in time so that everything from the developer to the CI servers to the production system is identical.
Essentially, you want `poetry install` without the dev requirements.

This functionality is provided out of the box by `stew build`, which creates a pip-installable package from the lock file that you can then stash in a private storage of your choice or pass around your deployments.


## How to provision a business production system / how to freeze your project for "offline" distribution

You can keep `poetry` and `stew` off your production environment by creating a frozen archive of your application or library from your CI servers (docker used as example):

- Use the `stew build` tool which:
    - performs a `poetry build` on your project
    - calls `pip download` based on the content of the lock file
    - Moves the artifacts to the `.wheels` folder of your repo
- Recommended: Use the `--python` switch when calling `stew build` to specify which python executable to use! Make sure to use a python interpreter that matches the os/arch/bits of the system you want to provision.

The content in `.wheels` can then be zipped and moved around. A typical scenario is to push it into a Docker Container:

- Include the `.wheels` folder into your Docker build context
- In your Dockerfile:
    - ADD the `.wheels` folder
    - Manage the `pip` version! Either update it to latest, or pin it to something.
    - Prepare a python environment
        - Use `python -m venv <location>` to create a virtual environment natively.
        - Note the executable location... typically (`location/bin/python` or `location/Scripts/python.exe`)
    - Install your application into the python environment you just created:
        - Use `<venv-python-executable> -m pip install <your-package> --no-index --find-links <wheels-folder-location>`
    - You may delete the `.wheels` folder if you want. Consider keeping a copy of the lock file within the docker image, for reference.

To make sure you use the python interpreter that matches the os/arch/bits of the system you want to provision, you can run `stew build` directly when building the container image.
In order to do so without packaging `stew` in production, you can use [multi-stage builds](https://docs.docker.com/develop/develop-images/multistage-build/).

## How to hook your IDE with the virtual environment

If your IDE supports poetry, it should detect and use the `pyproject.toml` file.

To set it up manually:

1. Call `poetry install` from the location of the `pyproject.toml` file
1. Obtain the location of the virtual environment (i.e.: `poetry env list --full-path`)
1. Configure your IDE to use the python interpreter from that location

Your IDE should proceed to analyze the environment and will pick up all imports automatically, 
regardless of your PYTHONPATH or your working directory.
Since the local source is editable, any change to the source code will be reflected on the next interpreter run.

If you use the multiple-projects approach, you should hook your IDE to the `pydev` environment. See [this documentation](./README_MULTIPLE_LIBRARIES.md) for more information.


## Using the virtual environment without activating it

Using the correct interpreter is all you need to do. 
There is no activation script or environment variables to set up: the interpreter executable inside the virtual environment folder is a fully bootstrapped and isolated environment.

- A python dockerfile may call `<venv-python-exec>` directly in the dockerfile's CMD
- A service that spawns other processes should receive the path to the `<venv-python-exec>`

[Use the `-m` switch](https://docs.python.org/3/using/cmdline.html#cmdoption-m) in order to launch your app!
