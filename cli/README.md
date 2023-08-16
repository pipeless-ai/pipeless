# Pipeless CLI

Pipeless is a framework to build and deploy multimodal perception apps in minutes without worrying about multimedia pipelines.
Pipeless CLI is the CLI component of the framework.

## Install

Run the following command:

```console
pip install pipeless-ai-cli
```

## Usage

```console
pipeless --help
```

See the main docs for the [getting started](https://github.com/miguelaeh/pipeless) guide.

## Development

We use `poetry` to manage dependencies.

The CLI depends on the core component. Both components are released separatedly.

The `commands` directory contains all the commands that the CLI supports.
The `templates` directory contains default application templates that users can select for their app scafolding.
