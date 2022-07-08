# Upgrading from 2.x to 3.x

## Poetry is not found

You need to install poetry to the system and ensure it's available through the path as `poetry`.

A common challenge is to make this work on a CI server.
Feel free to use or refer to this [GitHub Action](README.md#GitHub Action) ([source](action.yml)).

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
