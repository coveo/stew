# Upgrading from 3.x to 4.x

## Uninstall `coveo-stew`

For instance, if you installed it with pipx:

```bash
pipx uninstall coveo-stew
```

After uninstalling, validate that the `stew` command is no longer available.


## Install as a plugin

Installing the plugin depends on how you installed poetry [docs](https://python-poetry.org/docs/plugins/#using-plugins).

For instance, if you installed with `pipx`, you can install the plugin with:

```bash
pipx inject poetry coveo-stew
```


## Adjust usages

Change all occurrences of `stew` to `poetry stew`:

- `stew ci` becomes `poetry stew ci`
- `stew pull-dev-requirements` becomes `poetry stew pull-dev-requirements`

Change occurrences of `stew build --directory <dir>` to `poetry stew build --target <dir>`.
- The `--directory` option conflicted with poetry's global `--directory` option, so it was renamed to `--target` to mimick `pip install --target`.


## Adjust your `pyproject.toml`

### Migrate to the new `[project]` section

The `[tool.poetry]` section is now deprecated and replaced by the `[project]` section.
- https://python-poetry.org/docs/pyproject/#the-project-section
- https://packaging.python.org/en/latest/specifications/pyproject-toml/#declaring-project-metadata-the-project-table

## Use the new GitHub Action

If you were using the `coveo/stew` GitHub Action, you need to update it to use `coveo/stew/plugin` instead:

```yaml
- uses: coveo/stew/plugin@main
```

# Upgrading from 2.x to 3.x

## Poetry is not found

You need to install poetry to the system and ensure it's available through the path as `poetry`.

A common challenge is to make this work on a CI server.
Feel free to use or refer to this [GitHub Action](README.md#GitHub-Action) ([source](action.yml)).

Here's an example on how to make it work within a Dockerfile, without pipx:

```
RUN python -m pip install --upgrade pip setuptools wheel
RUN python -m venv /stew
RUN /stew/bin/python -m pip install coveo-stew
RUN chmod a+x /stew/bin/stew
RUN ln --symbolic /stew/bin/stew /usr/bin/stew

RUN python -m venv /poetry
RUN /poetry/bin/python -m pip install poetry
RUN chmod a+x /poetry/bin/poetry
RUN ln --symbolic /poetry/bin/poetry /usr/bin/poetry
```

## mypy, black is not found

You need to include these dependencies into your `pyproject.toml`, 
typically in the `[tool.poetry.dev-dependencies]` section:

```toml
[tool.poetry.dev-dependencies]
black = "*"
mypy = "*"
```


## stew build fails with missing hashes

Add this to your `pyproject.toml`:

```toml
[tool.stew]
build-without-hashes = true
```

Explanation:

The `stew build` command changed considerably. 

In the past, we were analyzing the active virtual environment 
and matching the information against the lock file to download the proper packages for your platform.

This was a "hack", due to a bug in earlier versions of `poetry`, where the `poetry export`
did not correctly output some constraints and caused packages to be installed on the wrong OS.

This bug has been fixed, and so the hack in `coveo-stew` was removed. 
The process is now much simpler (extra arguments removed for readability):

- We call `poetry export --output temp-requirements.txt`
- We call `pip wheel -r temp-requirements.txt --target <wheels-folder>`

Unfortunately, it was reported that _some_ packages don't have a hash in the `poetry.lock` file,
and this causes `pip wheel` to fail by design when you mix packages with hashes and with no hashes.

To circumvent this, add the `build-without-hashes` switch to your configuration 
so that `stew` adds `--without-hashes` to the `poetry export` command.

probable cause: 
- https://github.com/pypi/warehouse/pull/11775

related poetry issues:
- https://github.com/python-poetry/poetry/issues/5967
- https://github.com/python-poetry/poetry/issues/5970
