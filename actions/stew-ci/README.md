# Launch "stew ci" on a project

This action checkouts the code, installs python, poetry and stew, and proceeds to run "stew ci" on a python project.

## Usage

```yml
jobs:
  stew-ci:
    runs-on: ubuntu-latest
    steps:
      - uses: coveo/stew/actions/stew-ci@main
        with:
          python-version: "3.10"
          project-name: your-project-name
```
