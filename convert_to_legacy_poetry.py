#!/usr/bin/env python3
"""
Script to convert modern pyproject.toml using [project] format to the legacy [tool.poetry] format.
This is useful for compatibility with older Poetry versions.
"""

import os
import sys

import tomlkit


def convert_to_legacy_poetry(pyproject_path):
    """
    Convert a modern pyproject.toml to use the legacy [tool.poetry] format.
    """
    print(f"Converting {pyproject_path} to legacy Poetry format...")

    with open(pyproject_path, "r", encoding="utf-8") as f:
        pyproject = tomlkit.parse(f.read())

    # Make a backup of the original file
    backup_path = f"{pyproject_path}.bak"
    print(f"Creating backup at {backup_path}")
    with open(backup_path, "w", encoding="utf-8") as f:
        f.write(tomlkit.dumps(pyproject))

    # Check if the file already has the legacy format
    if "project" not in pyproject:
        print("File is already in legacy format or has no 'project' section. No conversion needed.")
        return

    # Ensure tool.poetry exists
    if "tool" not in pyproject:
        pyproject["tool"] = tomlkit.table()
    if "poetry" not in pyproject["tool"]:
        pyproject["tool"]["poetry"] = tomlkit.table()

    # Transfer fields from project to tool.poetry
    project_data = pyproject["project"]

    # Handle name, version, description
    if "name" in project_data:
        pyproject["tool"]["poetry"]["name"] = project_data["name"]

    if "version" in project_data:
        pyproject["tool"]["poetry"]["version"] = project_data["version"]

    if "description" in project_data:
        pyproject["tool"]["poetry"]["description"] = project_data["description"]

    # Handle authors - convert from dict format to string format "Name <email>"
    if "authors" in project_data:
        authors = []
        for author in project_data["authors"]:
            if isinstance(author, dict):
                name = author.get("name", "")
                email = author.get("email", "")
                if email:
                    authors.append(f"{name} <{email}>")
                else:
                    authors.append(name)
            elif isinstance(author, str):
                authors.append(author)

        pyproject["tool"]["poetry"]["authors"] = tomlkit.array(authors)

    # Handle keywords
    if "keywords" in project_data:
        pyproject["tool"]["poetry"]["keywords"] = project_data["keywords"]

    # Handle python version requirement
    if "requires-python" in project_data:
        pyproject["tool"]["poetry"]["dependencies"] = pyproject["tool"]["poetry"].get(
            "dependencies", tomlkit.table()
        )
        pyproject["tool"]["poetry"]["dependencies"]["python"] = project_data["requires-python"]

    # Handle license
    if "license" in project_data:
        if isinstance(project_data["license"], dict) and "text" in project_data["license"]:
            pyproject["tool"]["poetry"]["license"] = project_data["license"]["text"]
        else:
            pyproject["tool"]["poetry"]["license"] = project_data["license"]

    # Handle readme
    if "readme" in project_data:
        pyproject["tool"]["poetry"]["readme"] = project_data["readme"]

    # Handle dependencies
    if "dependencies" in project_data:
        if "dependencies" not in pyproject["tool"]["poetry"]:
            pyproject["tool"]["poetry"]["dependencies"] = tomlkit.table()

        for dep in project_data["dependencies"]:
            # Parse dependency string
            if isinstance(dep, str):
                parts = dep.split()
                name = parts[0]
                version = " ".join(parts[1:]) if len(parts) > 1 else "*"
                pyproject["tool"]["poetry"]["dependencies"][name] = version
            elif isinstance(dep, dict):
                # Handle the dict format if present
                name = next(iter(dep))
                pyproject["tool"]["poetry"]["dependencies"][name] = dep[name]

    # Handle URLs
    if "urls" in project_data:
        urls = project_data["urls"]
        if "repository" in urls:
            pyproject["tool"]["poetry"]["repository"] = urls["repository"]
        if "homepage" in urls:
            pyproject["tool"]["poetry"]["homepage"] = urls["homepage"]
        if "documentation" in urls:
            pyproject["tool"]["poetry"]["documentation"] = urls["documentation"]

    # Handle scripts -> tool.poetry.scripts
    if "scripts" in project_data:
        if "scripts" not in pyproject["tool"]["poetry"]:
            pyproject["tool"]["poetry"]["scripts"] = tomlkit.table()

        for script_name, script_path in project_data["scripts"].items():
            pyproject["tool"]["poetry"]["scripts"][script_name] = script_path

    # Handle entry-points - mapping to poetry's format
    if "entry-points" in project_data:
        for group_name, entries in project_data["entry-points"].items():
            # Handle Poetry plugin format specially
            if group_name == "poetry.application.plugin":
                # Create the plugins section if it doesn't exist
                if "plugins" not in pyproject["tool"]["poetry"]:
                    pyproject["tool"]["poetry"]["plugins"] = tomlkit.table()

                # Add the plugin group as a direct entry
                plugin_group = '"poetry.application.plugin"'
                if plugin_group not in pyproject["tool"]["poetry"]["plugins"]:
                    pyproject["tool"]["poetry"]["plugins"][plugin_group] = tomlkit.table()

                # Add plugin entries
                for entry_name, entry_point in entries.items():
                    pyproject["tool"]["poetry"]["plugins"][plugin_group][entry_name] = entry_point
            else:
                # Handle other entry points
                group_key = "scripts" if group_name == "console_scripts" else group_name

                if group_key not in pyproject["tool"]["poetry"]:
                    pyproject["tool"]["poetry"][group_key] = tomlkit.table()

                for entry_name, entry_point in entries.items():
                    pyproject["tool"]["poetry"][group_key][entry_name] = entry_point

    # Remove the original project section
    del pyproject["project"]

    # Write the modified content back to the file
    with open(pyproject_path, "w", encoding="utf-8") as f:
        f.write(tomlkit.dumps(pyproject))

    print(f"Successfully converted {pyproject_path} to legacy Poetry format.")
    print(f"Original file backed up to {backup_path}")


if __name__ == "__main__":
    pyproject_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pyproject.toml")

    if len(sys.argv) > 1:
        pyproject_path = sys.argv[1]

    convert_to_legacy_poetry(pyproject_path)
