# How to install an editable version of the plugin

It's really useful to be able to add the plugin to poetry in editable mode.

The command `poetry self add ./` does not work.

We can get around this with pipx:

```bash
pipx install poetry
pipx inject poetry ./ --editable
```