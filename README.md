# Upgrading from 3.x?

The 4.0 update is a major breaking change, 
as `coveo-stew` was rewritten as a Poetry plugin instead of a standalone CLI tool.

Please refer to the [upgrade guide](./README_UPGRADE.md#upgrading-from-3x-to-4x) for more information and resolution steps.


# Upgrading from 2.x?

The 3.0 update contains breaking changes:
`poetry`, `mypy` and `black` are no longer distributed with `coveo-stew`.

Please refer to the [upgrade guide](./README_UPGRADE.md#upgrading-from-2x-to-3x) for more information and resolution steps.


# coveo-stew

coveo-stew delivers a complete Continuous Integration (CI) and Continuous Delivery (CD) solution
using [poetry](https://python-poetry.org) as its backend.


## CI tools
- Config-free pytest, mypy and black runners
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


# Prerequisites
*Changed in 4.0*: You need poetry 1.8 or higher.
*Changed in 4.0*: Poetry must have been installed with python 3.9 or higher, but you can still use it on projects requiring older versions of python.

*Changed in 3.1*: You need python 3.9 or higher, but you can still use it on projects requiring older versions of python.
*Changed in 3.0*: `poetry` is no longer provided out-of-the-box.

You need [poetry](https://python-poetry.org/) installed on your system, and it must be available through the `PATH`.

While it is compatible with older versions, old poetry issues
such as [this](https://github.com/python-poetry/poetry/issues/3189)
and [this](https://github.com/python-poetry/poetry/issues/3254)
will cause `stew` to misbehave.

If you need to work with an older version of poetry,
consider using `coveo-stew < 3.0` which had workarounds implemented around these issues.


# Installation

Coveo-stew is a poetry plugin.

Depending on how you installed poetry, you may need to install it differently.

See the [poetry documentation](https://python-poetry.org/docs/plugins/#using-plugins) for more information 
and alternative installation methods.

It is recommended to install using [pipx](https://github.com/pipxproject/pipx):

```shell
pipx install poetry
pipx inject poetry coveo-stew
```


# GitHub Action

This action checkouts the code, installs python, poetry and stew, and proceeds to run "stew ci" on a python project.

*Changed in 4.0*: `pipx` is no longer installed by default, since it is built into to the GitHub runners.
If you need to install it manually (e.g.: self-hosted runners), here's how we used to do it:

```yaml
    - name: Prepare pipx path
      shell: bash
      run: echo "$HOME/.local/bin" >> $GITHUB_PATH

    - name: Upgrade python tools and install pipx
      shell: bash
      run: python -m pip install --upgrade pip wheel setuptools pipx --user --disable-pip-version-check

    - name: poetry, poetry export, and stew
      shell: bash
      run: |
        python -m pipx install "poetry$POETRY_VERSION"
        python -m pipx inject poetry poetry-plugin-export
        python -m pipx install "coveo-stew$COVEO_STEW_VERSION"
```

## Usage

*Changed in 4.0*: The action was renamed to `coveo/stew/plugin`.

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

See additional options and documentation in [the action file.](plugin/action.yml)


## GitHub Action Step Report

When running in a GitHub context, a step summary will automatically be generated.
This summary can be seen in the `Summary` tab of a workflow run view in GitHub.

*Changed in 4.0*: It is no longer possible to disable the step report generation.


# Repository Structure

Please read these guides in order to learn how to organize your repository for maximum compatibility:

- [For a single library](README_SINGLE_LIBRARY.md)
- [For multiple libraries](README_MULTIPLE_LIBRARIES.md)


# Commands

## General command usage

Unless a project name is specified, commands will operate on all projects in a git repository based on the current working folder:

- `poetry stew <command>`
    - Perform a command on all projects
- `poetry stew <command> --help`
    - Obtain help about a particular command


Some commands allow specifying a project name:

- `poetry stew <command> <project-name>`
    - Perform the command on all projects with `<project-name>` in their name (partial, case-insensitive)
    - e.g.: `stew ci tools` will run on `tools`, `tools-common`, `my-tools`, etc.
- `poetry stew <command> <project-name> --exact-match`
    - Disable partial project name matching
    - e.g.: `stew ci tools --exact-match` will run on `tools` but not on `tools-common`, `my-tools`, etc.
- `poetry stew <command> .<path>`
    - **v3.1.3** Only consider the project at this location
    - The path must start with `.`
    - Nested projects will not run
    - e.g.: `stew ci .` will only run on the project in the current folder
    - e.g.: `stew ci ./tools` will only run on the project in the `tools` folder

The main commands are explained below.


## `poetry stew ci`

The main show; it runs all CI tools on one or multiple projects.

Errors will show in the console, and junit xml reports will be generated inside the `.ci` folder.

Without configuration, this command will run the following checks:

- mypy (using opinionated, strict rules)
  - Note: `mypy` is not provided with `coveo-stew`. See [builtin-runners](#builtin-runners) for info.
- poetry check
- stew check-outdated

Options:

- `--fix` will reformat the code if `black` fails. Additional fix routines may be added in the future.
- `--check <runner>` will launch only that runner. This option can be repeated.
- `--skip <runner>` will skip that runner. Takes precedence over `--check`. This option can be repeated.
- `--quick` skips running `poetry install --remove-untracked` before running the checks.
  - **v3.0.30**: You can now customize which checks to run when `--quick` is specified. See the [quick](#configuration) configuration option.
- `--extra <extra>` *(v3.1.1)* will install the specified extra(s) for this run. Can be specified multiple times.
- `--all-extras` *(v3.1.1)* will install all extras for this run.
- `--no-extras` *(v3.1.1)* will not install any extra for this run.

The configuration for this feature is explained in more details in the [runners](#runners-stew-ci) section.

## `poetry stew build`

Store the project and its **locked dependencies** to disk, so it can be installed without contacting a `pypi` server.

Optimally used to create truly repeatable builds and workflows (e.g.: containerized images, cloud storage, etc).

The folder can later be installed offline with `pip install --no-index --find-links <folder> <project-name>`.


Options:

- `--target` specifies where the wheels should be downloaded. (*Changed in v4.0*: renamed `--directory` to `--target`) 
- `--python` may be used to target a different python. It's important to use the same python version, architecture and OS than the target system.

**Make sure your target `<folder>` is clean**: Keep in mind that `pip` will still use the `pyproject.toml` constraints when installing, not `poetry.lock`.

*The locked version system works when the locked version is the only thing that `pip` can find in the `<folder>`.*


## `poetry stew check-outdated` and `poetry stew fix-outdated`

Checks for out-of-date files or automatically update them.

Summary of actions:
- `poetry lock` if `pyproject.toml` changed but not the `poetry.lock`
- `poetry stew pull-dev-requirements` if a pydev project's dev-requirements are out of sync


## `poetry stew pull-dev-requirements`

Only useful on `pydev` projects (see about [multiple-libraries](README_MULTIPLE_LIBRARIES.md)).
It pulls the group requirements from the local projects in order to aggregate them into the requirements of the root project.

Note: This command uses the non-optional groups to find dependencies (Changed in v4.0, previously it only looked at the group named dev).
These can be defined as `tool.poetry.group.<group-name>.dependencies`.

*Changed in 4.0*: 
- All non-optional groups will be pulled (not only the one named `dev`)
- The generated group in the pydev project is named `stew-pydev` instead of `dev`


## `poetry stew bump`

Calls `poetry lock` on all projects.


## `poetry stew refresh`

Calls `poetry install` on all projects.


## `poetry stew fresh-eggs`

Clears the `.egg-info` folder from your projects. Usually followed by a `poetry install` or a `stew refresh`.

Use this if you change a `[tool.poetry.scripts]` section, else the changes will not be honored.


## `poetry stew locate <project>`

Returns the path to a project:

```
$ poetry stew locate coveo-stew
/home/jonapich/code/stew/coveo-stew
```

# Configuration

## stew

Configuration is done through the `pyproject.toml` file; default values are shown:

```
[tool.stew]
build-without-hashes = false
pydev = false
build-dependencies = {}
extras = []
all-extras = false
quick = {}
```

- **build-without-hashes**: Disables hashes when calling `pip` to download dependencies during `stew build`.
- **pydev**: See the [multiple-libraries](README_MULTIPLE_LIBRARIES.md) guide.
- **build-dependencies**: You can specify additional dependencies to be installed during `stew build`.
  - The format is the same as poetry dependencies: `name = "version"` or `name = { version = "version", ... }`
- **extras**: A list of extras to install during `stew build` and `stew ci`.
  - *(v3.1.1)* Can be specified at execution time with `stew ci --extra <this> --extra <that>`.  
- **all-extras**: If true, all extras will be installed during `stew build` and `stew ci`. Overrides the `extras` list.
  - *(v3.1.1)* Can be specified at execution time with `stew ci --all-extras` and `stew ci --no-extras`. 
- **quick**: *(v3.0.30)* Controls which checks are skipped when calling `stew ci --quick`. 
  - The format is a dictionary with either the `check` or `skip` key, followed by a list of runners.
  - The behavior is identical to the `--check` and `--skip` options.
  - e.g.: skip these checks `quick = { skip = ["poetry-check", "check-outdated", "poetry-build", "pytest"] }`
  - e.g.: only run these checks `quick = { check = ["mypy", "black"] }`

## stew ci
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


# Runners (stew ci)

*Changed in coveo-stew 3.0*: mypy and black are no longer provided out-of-the-box.

In order to use a builtin or custom runner, you must have it installed. These locations are supported:

- Recommended: The runner is in the project's virtual environment (most likely as a dev dependency in `pyproject.toml`)
- Alternative: The runner is installed in your system and available through the PATH

We strongly suggest pinning them to your
`pyproject.toml` file in the `[tool.poetry.test.dependencies]` section.

This way, mypy won't surprise you with new failures when they release new versions! 😎

Note: You can override and customize most runners by [rewriting them as custom runners.](#custom-runners)


## Builtin Runners

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

Runs `poetry stew check-outdated`.

Note: This runner cannot be overridden, but it can be disabled.


### offline-build

Runs `poetry stew build` to a temporary folder and ensures that pip is able to reinstall everything from there.

Note: This runner cannot be overridden, but it can be disabled.


## Custom Runners

You can add your own runners to `poetry stew ci`.
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

# using `executable`, you can create multiple custom runners with the same executable:
[tool.stew.ci.custom-runners.ruff-check]
executable = "ruff"
working-directory = "project"
check-args = ["check", "."]
autofix-args = [ "check", "--fix", "."]

[tool.stew.ci.custom-runners.ruff-format]
executable = "ruff"
working-directory = "project"
check-args = ["format", "--check", "."]
autofix-args = ["format", "."]
```

When a builtin runner such as pytest is redefined as a custom runner, you must provide all the arguments.
In this case, not passing `--junitxml` would mean that we lose the report that used to be in the `.ci/` directory.


### Options

- executable: You can specify the executable name if it's different from the tool's name.
  - Runners are called through `python -m <executable>` first to see if it's installed in the virtual environment, else through the shell.
  - Using `executable`, you can create multiple custom runners with the same executable (e.g.: `ruff check` vs `ruff format`) 
- check-args: The arguments to invoke the check.
- autofix-args: The arguments to invoke the autofix. Provide the empty string "" in order to run without arguments.
- check-failed-exit-codes: A list of ints denoting the exit codes to consider "failed" (anything else will be "error"). 0 is always a success. default is `[1]`.
- create-generic-report: Whether to create a generic pass/fail JUnit report for this check.
- working-directory: The default is "project" which corresponds to the project's `pyproject.toml` file. You can change it to "repository" in order to run from the root.
- name: You can specify the module name if it differs from the name of the tool.
  - Deprecated: name must be unique. This has been replaced by `executable`.

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

This functionality is provided out of the box by `poetry stew build`, which creates a pip-installable package from the lock file that you can then stash in a private storage of your choice or pass around your deployments.


## How to provision a business production system / how to freeze your project for "offline" distribution

You can keep `poetry` and `coveo-stew` off your production environment by creating a frozen archive of your application or library from your CI servers (docker used as example):

- Use the `poetry stew build` tool which:
    - performs a `poetry build` on your project
    - calls `pip download` based on the content of the lock file
    - Moves the artifacts to the `.wheels` folder of your repo
- Recommended: Use the `--python` switch when calling `poetry stew build` to specify which python executable to use! Make sure to use a python interpreter that matches the os/arch/bits of the system you want to provision.

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
In order to do so without packaging `coveo-stew` in production, you can use [multi-stage builds](https://docs.docker.com/develop/develop-images/multistage-build/).

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
