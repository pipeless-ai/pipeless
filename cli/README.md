# Pipeless CLI

This directory contains the CLI component of the framework.

# Development

We use `poetry` to manage dependencies.

The CLI depends on the core component. Both components are released separatedly.\

The `commands` directory contains all the commands that the CLI supports.
The `templates` directory contains default application templates that users can select for their app scafolding.

## To add new dependencies:

```
poetry install <package-name>
```
