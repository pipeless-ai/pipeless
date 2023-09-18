<p align="center">
  <a href="https://pipeless.ai">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="assets/pipeless-400x400-rounded.png">
      <img src="assets/pipeless-400x400-rounded.png" height="128">
    </picture>
    <h1 align="center">Pipeless</h1>
  </a>
</p>

<p align="center">
  <a aria-label="Pipeless logo" href="https://pipeless.ai">
    <img src="https://img.shields.io/badge/MADE%20BY%20Pipeless%20ai-000000.svg?style=for-the-badge&logo=Pipeless&labelColor=000">
  </a>
  <a aria-label="Python version" href="https://pypi.org/project/pipeless-ai/">
    <img alt="" src="https://img.shields.io/pypi/v/pipeless-ai?style=for-the-badge&label=PyPi&labelColor=000000">
  </a>
  <a aria-label="License" href="https://github.com/miguelaeh/pipeless/blob/main/license.md">
    <img alt="" src="https://img.shields.io/pypi/l/pipeless-ai?style=for-the-badge&labelColor=000000">
  </a>
  <a aria-label="Join the community on GitHub" href="https://github.com/miguelaeh/pipeless/discussions">
    <img alt="" src="https://img.shields.io/badge/Join%20the%20community-black.svg?style=for-the-badge&logo=&labelColor=000000&logoWidth=20">
  </a>
</p>

<div align="center">
   <p>An open-source computer vision framework.</p>
   <p>Easily create and deploy applications that analyze and manipulate video streams in real-time without the complexity of building and maintaining multimedia pipelines.</p>
   <p>Join us in our mission and contribute to make the day to day life of computer vision developers easier!</p>

   <br />

   <div>
      <img height="350" align="center" src="assets/pipeless-yolo.gif">
      <img width="50%" align="center" src="assets/yolo-example.png" />
   </div>

   <br /><br />
</div>

Pipeless ships all the features you need to create and deploy efficent computer vision applications that work in real-time. Just like you implement specific functions in serverless web applications, Pipeless simply requires you to implement certain hooks to process any stream from any source.

Pipeless provides industry-standard models that you can use out-of-the-box or easily bring your own custom model. The Pipeless worker contains a built-in ONNX Runtime allowing you to run inference using any compatible model.

With Pipeless, you can deploy either on edge devices or to the cloud thanks to our container images, and it also provides a built-in communication layer to boost the stream processing speed to any desired framerate out-of-the-box, by automatically distributing the frame processing.

Futhermore, you can easily extend the feature set thanks to the plugins system. For example, there are plugins to handle events on real-time with Kafka, use YOLOv8 models, automatically draw inference results over the original video, and many others.

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

## Built-in ONNX Runtime

With the built-in ONNX Runtime you can run inference over the video frames out-of-the box by simply providing a model.

We are moving the documentation to its own site to improve the search experience. Please find [here](https://pipeless.ai/docs/v0/inference) the documentation about running inference with the ONNX runtime.

## Supported stream formats 📌

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
