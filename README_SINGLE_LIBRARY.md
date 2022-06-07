# Setup for a single library 

Generally speaking, a single poetry-backed library should work out of the box with `stew` with no additional configuration. 

However, we cannot assume that all setups will work. To maximize compatibility with `stew`, 
setup your project according to one of the two options below.


## Option 1: At the root of the repository

This setup is only suitable for single-library repositories.

1. The `pyproject.toml` file is at the root of the repository (e.g.: `/pyproject.toml`)
2. A folder that matches the name of your import, next to the `pyproject.toml` file (e.g.: `/coveo_stew/`)
3. An `__init__.py` file inside the importable folder  (e.g.: `/coveo_stew/__init__.py`)

The current repository uses that setup.


## Option 2: In a folder

This setup is actually the [multiple library setup](./README_MULTIPLE_LIBRARIES.md) with just one library:

1. The `pyproject.toml` file is contained in a folder somewhere in the repository (e.g.: `/src/python/pyproject.toml`)
2. There's a folder that matches the name of your module import, next to the `pyproject.toml` file (e.g.: `/src/python/coveo_systools/*.py`)
3. An `__init__.py` file inside the importable folder  (e.g.: `/src/python/coveo_systools/__init__.py`)

As a reference, take a look at the [coveo-python-oss repository](https://github.com/coveooss/coveo-python-oss).
