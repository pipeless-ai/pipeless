<div align="center">
  <img src="assets/pipeless-logo-w300.png" alt="Pipeless logo" />
</div>

![X (formerly Twitter) Follow](https://img.shields.io/twitter/follow/pipeless_ai?color=%230000ff)

Pipeless is an open source multimedia framework with focus on computer vision.

With Pipeless, developers can create and deploy applications that analyze and manipulate audio and video in real time in just minutes, allowing them to focus on their applications instead of on creating and maintaining multimedia pipelines.

You can build applications in less than 15 lines of code thanks to the built-in models or you can easily bring your own models for complex use cases.

Pipeless run either locally or in the cloud and can be easily deployed thanks to our container images.

For example, you can build thing like:

https://github.com/miguelaeh/pipeless/assets/36923089/53012dea-5b82-44e4-9120-db90b9f11765

With just with these simple lines of code:

![Cats recognition code](assets/cats-code.png)

[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/release/python-3100/)

## Index 📚

- [Requirements](#requirements-%EF%B8%8F)
- [Installation](#installation-%EF%B8%8F)
   - [Using Docker](#using-docker)
- [Getting started](#getting-started-)
   - [Create a Project](#create-a-project)
   - [Project Structure](#project-structure)
   - [Media Processing](#media-processing)
   - [Run Your App](#run-your-app)
   - [Configuration](#configuration)
- [Current State](#current-state-)
- [Ready to use models](#ready-to-use-models)
   - [Tensorflow models](#tensorflow-based-models)
- [Plugins](#plugins)
   - [List of available plugins](#available-plugins)
- [Troubleshooting](#troubleshooting-)
- [Examples](#examples-)
- [Contributing](#contributing-)
- [License](#license-)

## Requirements ☝️

* Python (tested with version `3.10.12`)
* **Gstreamer 1.20.3**. Verify with `gst-launch-1.0 --gst-version`. Installation instructions [here](https://gstreamer.freedesktop.org/documentation/installing/index.html?gi-language=python)

### Note about macOS

The latest version of macOS (Ventura) comes with Python `3.9` by default. You can install version `3.10` with:

```console
brew install python
```

Also, to install Gstreamer in macOS use the following instead of the upstream instructions to ensure all the required packages are installed:

```console
brew install gstreamer
```

## Installation 🛠️

The following command installs the core (`pipeless-ai`) and the CLI (`pipeless-ai-cli`) into your system.

```console
pip install pipeless-ai pipeless-ai-cli
```

Test the installation with:

```console
pipeless --help
```

> NOTE: you may need to reload your shell for the new command to be available

### Using docker

Instead of installing locally, you can alternatively use docker and save the time of installing dependencies:

```console
docker run miguelaeh/pipeless --help
```

Find the whole container documentation [here](/package/README.md).

## Getting Started 🚀

Find the [getting started guide](https://pipeless.ai/docs/v0/getting-started) at the new docs.

### Create an application

```console
pipeless create project <name>
```

### Run the application

```console
pipeless run
```

### Configuration

We are moving the documentation to its own site to improve the search experience. Please find [here](https://pipeless.ai/docs/v0/configuration) the configuration section.

## Supported formats 📌

We are moving the documentation to its own site to improve the search experience. Please find [here](https://pipeless.ai/docs/v0/formats) the supported protocols and media formats.

## Ready to use models

We provide some modules containing a growing set of ready to use models for common cases. You can use them to develop your applications as fast as writing a couple lines of code. Each module has its own documentation, and the whole set of modules can be found [here](https://pipeless.ai/docs/v0/models).

## Plugins

The Pipeless plugin system allows you to add functionality to your application out-of-the-box.
Find the whole documentation about the Pipeless plugin system [here](https://pipeless.ai/docs/v0/plugins).

## Troubleshooting 🐞

Please check the [troubleshooting section here](https://pipeless.ai/docs/v0/troubleshooting).

## Examples 🌟

We provide some working applications under the `examples` directory, so you can easily run and play with them.

Find [here](https://pipeless.ai/docs/v0/examples) the whole list of examples and step by step guides.

## Contributing 🤝

Thanks for your interest in contributing! Contributions are welcome and encouraged. While we're working on creating detailed contributing guidelines, here are a few general steps to get started:

1. Fork this repository.
2. Create a new branch: `git checkout -b feature-branch`.
3. Make your changes and commit them: `git commit -m 'Add new feature'`.
4. Push your changes to your fork: `git push origin feature-branch`.
5. Open a pull request describing your changes.

We appreciate your help in making this project better!

Please note that for major changes or new features, it's a good idea to discuss them in an issue first so we can coordinate efforts.

## License 📄

This project is licensed under the [Apache License 2.0](LICENSE).

### Apache License 2.0 Summary

The Apache License 2.0 is a permissive open-source license that allows you to use, modify, and distribute this software for personal or commercial purposes. It comes with certain obligations, including providing attribution to the original authors and including the original license text in your distributions.

For the full license text, please refer to the [Apache License 2.0](LICENSE).

## Notable Changes

Notable changes indicate important changes between versions. Please check the [whole list notable changes](https://pipeless.ai/docs/v0/changes).
