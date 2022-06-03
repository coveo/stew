# Considerations for multi-projects repositories 

Follow this guide to configure your repository to work with multiple projects.


## Repository structure

To combine multiple projects in a repository, you need to adhere to the following:

1. At a defined root, such as the root of your repository or a folder within, create a new `pyproject.toml` file. It will be the dev environment; we will come back to this soon.
2. Python libraries should then exist within that folder's hierarchy, each of them in a dedicated folder. The dedicated folder doesn't need to be in the root.

[The current repository](https://github.com/coveooss/coveo-python-oss) is a good example. The `pydev` environment is in the root's `pyproject.toml`, and subfolders contain the python libraries


## Python libraries structure

Each individual python library must be able to work on its own, meaning that:

1. It has a dedicated folder (e.g.: `coveo-systools`). 
2. It has `pyproject.toml` file in that dedicated folder. 
3. The dedicated folder has a folder that matches the name of the project (e.g.: `coveo_systools`)
4. The project folder contains the "first" `__init__.py` in that hierarchy.

The expected setup is also defined as the "sub-folder" setup (Option 2!) in [the single library setup guide](./README_SINGLE_LIBRARY.md)


## Developer environment's `pyproject.toml`

The root `pyproject.toml` needs to be designed so that:

1. It's `poetry check` compliant.
2. The `[tool.poetry.dependencies]` section should link to each subproject using a relative path reference.
3. The `[tool.poetry.dev-dependencies]` must not be used. You will generate it.
4. The `[tool.stew]` section has `pydev=true`.

Here's an example:

```
[tool.poetry]
name = "dev-environment"
version = "0.0.1"
description = "virtual environment bootstrap for developers"
authors = ["..."]

[tool.poetry.dependencies]
python = ">=3.8"
local-library = { path = 'local-library/', develop = true }
something-else = { path = 'lib/other/something-else/', develop = true }

[tool.stew]
pydev = true

[build-system]
requires = ["poetry_core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
```

You can then proceed to generate the `[poetry.tool.dev-dependencies]` section and create your virtual environment:

```
$ stew pull-dev-requirements
$ poetry update
```

The pydev environment has some caveats:

- It cannot be packaged, published or even pip-installed.
- `stew ci` will skip it.
- the `tool.poetry.dev-dependencies` section is reserved, can be generated and updated through stew's `pull-dev-requirements` and `fix-outdated` commands.

The reason we generate dev requirements is that `poetry install` will not install `dev-requirements` of dependencies.
Since all the local projects are dependencies, the `pull-dev-requirements` script will inspect each of them
in order to aggregate their dev requirements into the pydev environment.

When you add or remove dev-dependencies, run `pull-dev-requirements` again.
When you change the constraint of a dev-dependency, just run `stew bump` or `poetry update` to lock the new version.


# How to depend on a local python library

Python libraries (i.e.: not the pydev one!) may reference other local libraries using a relative path.

This is not particularly well handled by poetry and will cause problems with some operations such as "poetry build". 
We leverage poetry's `path` constraint in a very specific way to make it work:

```
[tool.poetry.dependencies]
my-package = { version = "^2.4" }

[tool.poetry.dev-dependencies]
my-package = { path = "../my-package/" }
```

Essentially, the behavior we're looking for:

- Through `pip install`, it will obtain the latest `^2.4` from `pypi.org`
- Through `poetry install`, which is only meant for development, the source is fetched from the disk

Note: Even if your libraries are not published to a `pypi` server, you can still use `stew build` to create an offline distribution.
This concept is particularly useful in business scenarios, for instance when dealing with containerized images and cloud storages.


# A note about the aggregated environment.

When you develop using the `pydev` environment, you are aggregating the dependencies of all the libraries into one environment.
This can cause some problems, for instance if your library A and B both require a 3rd party package Z, you must add Z to the `pyproject.toml` of both A and B.
If you omit Z in B, your pydev environment will still have Z because it was included with A. 
However, when you publish B, users will most likely run into an ImportError since Z was not specified there.

To circumvent this, `stew ci` mostly skips testing the `pydev` environment.
It will instead create an environment for A using A's `pyproject.toml` for tests.
Then it will create the environment for B using B's `pyproject.toml` for tests.
Technically, it should explode here if you forgot to include Z!

In other words, `stew` treats each individual library as a product on its own, while the `pydev` environment
only serves as a convenience for the developer to benefit from multiple editable python sources in a single environment.
