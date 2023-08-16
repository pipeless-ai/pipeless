# Pipeless

A framework to build and deploy multimodal perception apps in minutes without worrying about multimedia pipelines.

[![GitHub release](https://img.shields.io/github/release/migueaeh/pipeless.svg)](https://github.com/miguelaeh/pipeless/releases)
[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/release/python-3100/)

https://github.com/miguelaeh/pipeless/assets/36923089/56498c7b-485c-41d3-9346-35c069a78590

## Index 📚

- [Requirements](#requirements-%EF%B8%8F)
- [Installation](#installation-%EF%B8%8F)
- [Getting started](#getting-started-)
   - [Create a Project](#create-a-project)
   - [Project Structure](#project-structure)
   - [Media Processing](#media-processing)
   - [Run Your App](#run-your-app)
   - [Configuration](#configuration)
- [Current State](#current-state-)
- [Troubleshooting](#troubleshooting-)
- [Examples](#examples-)
- [Contributing](#contributing-)
- [License](#license-)

## Requirements ☝️

* Python (tested with version `3.10.12`)
* **Gstreamer 1.20.3**. Verify with `gst-launch-1.0 --gst-version`. Installation instructions [here](https://gstreamer.freedesktop.org/documentation/installing/index.html?gi-language=python)

## Installation 🛠️

The following command installs the `pipeless` CLI into your system. It also installs the `core` module as dependency.

```console
pip install pipeless-ai pipeless-ai-cli
```

> IMPORTANT: Please note it is `pipeless-cli`. If you install `pipeless` instead of `pipeless-cli` you will install only the core component.

## Getting Started 🚀

We recommend reading the getting starting guide, however, you can also go directly to the (examples)[examples] directory.

### Create a Project

Run the following command:

```console
pipeless create project <project-name>
```

By default, the above command will use an empty project template. You need to implement some functionality on it.

### Project structure

The `create project` command will create a directory under your project name with the following files:

* `app.py`: contains your `App` class. This file contains the implementation of your processing functions. For example, throwing inference on a CV model. Inot this file you will define the functions in charge of procesing the media frames.

* `config.yaml`: contains the configuration of the framework components. You can also override all configuration options via env vars starting with `PIPELESS_` followed by the config option name in capital letters.

### Media Processing

The processing steps are defined as methods of the `App` class. There are several processing stages that you can override:

#### Initial and final stages

These are represented by methods that are executed just once per stream.

They are tipically used when your app requires to execute some code before starting the processing or once the stream processing ends.

- `before`: contains code that is executed before processing any content from a stream
- `after`: contains code that is executed after the processing of a whole stream.

#### Processing stages

These are the stages that actually modify/learn/process the media streams. All of them receive a frame and **must** return a frame. The frames can be of any type(audio, video, text, metadata, ...).

- `pre_process`: code to execute to prepare a frame to be processed
- `process`: code for the actual frame processing
- `post-process`: code to execute after a frame is processed

These stages have been mainly defined for a proper logical code structure, there are no significant differences on how the code is executed on them.

#### Context

You app can maintain its own internal state. This is useful when you need to pass information between stages.

By default, an internal context is created and can be accessed via the `ctx` variable.

You can also define your own variables within the `App` class, however, note that if you override the constructor the context won't be initialized properly.

### Run Your App

To test your app execute the following from your app directory:

```console
pipeless run <component>
```

`<component>` must be one of `input`, `worker`, `output`, `all` (default).

When running your application locally, simply use `all` and everything will run automatically on the proper order.

#### Core Components

Pipeless has been designed for easy local execution but more important, to easily deploy to the cloud. Thus, it is split in 3 main components:

* `input`: Receives the media streams, demux and decode the streams.
* `worker`: Receives raw media frames, and processes them according to the user app. You can deploy any number of workers and the processing will be load balanced automatically using a round robin schedule. When deployed to the cloud this allows to reach **real time** processing even with each frame takes relatively long times to process. Note in that case, that each worker executes the `before` and `after` stages and that each worker has a different instance of the running app context.
* `output`: Receives the processed raw media frames, encodes and mux them into the proper container format for the output protocol provided by the user

Each component runs with independence of the others.

### Configuration

To configure your app you can use either env vars or the config file (`config.yaml`).

| Option | Description | Value(s)/Type | Env Var |
| ------ | ----------- | ------------- | ------- |
| `log_level` | Level of the logging|  `DEBUG`, `INFO`, `WARN`, `ERROR` | `PIPELESS_LOG_LEVEL` |
| `n_workers` | Number of workers deployed | int | `PIPELESS_N_WORKERS` |
| `input.address.host` | Host where the input component is running | `localhost` (string) | `PIPELESS_INPUT_ADDRESS_HOST` |
| `input.address.port` | Port of the input component process | `1234` (int) | `PIPELESS_INPUT_ADDRESS_PORT` |
| `input.video.enable` | Whether to enable to video input | `true` (boolean) | `PIPELESS_INPUT_VIDEO_ENABLE` |
| `input.video.uri`    | Uri of the input video to process. **Must** include the protocol (`file://`, `https://`, `rtmp://`, etc) | string | `PIPELESS_INPUT_VIDEO_URI` |
| `output.address.host` | Host where the output component is running | `localhost` (string) | `PIPELESS_OUTPUT_ADDRESS_HOST` |
| `output.address.port` | Port of the output component process | `1234` (int) | `PIPELESS_OUTPUT_ADDRESS_PORT` |
| `output.video.enable` | Whether to enable to video output | `true` (boolean) | `PIPELESS_OUTPUT_VIDEO_ENABLE` |
| `output.video.uri`    | Uri where to send the processed output video. **Must** include the protocol (`file://`, `https://`, `rtmp://`, etc) | string | `PIPELESS_OUTPUT_VIDEO_URI` |

## Current state 📌

Pipeless is in an alpha state. Below you can find the fields currently supported as well as the formats and protocols.

* Computer vision / video processing

For the input media we support almost any protocol and format (with several codecs). If you need a format that is not supported we appreacite the opening of a feature request or pull request.

Supported input protocols: `file`, `http(s)`, `rtmp`, `rtsp`, `rtp`, `tcp`, `udp`, `ftp`, ...
Supported input formats: `mp4`, `webm`, `mkv`, ... (several codecs supported for all of them)

The following table describes the supported output protocols and formats. New output protocols and formats are added constantly.

| Output Protocol | Output Format
| --------------- | ------------- |
| `screen`        | `raw` (Directly shown on the device screen) |
| `file`          | `mp4`         |

* Audio recognition / audio processing (in progress)

## Troubleshooting 🐞

* If the pipeline doesn't start and there is not apparent error even on the debug logs run the following command changing `<path>` by your file path:

```console
GST_DEBUG="*:3,GstVaapiPostproc:7,GstGLUploadElement:7" gst-launch-1.0 uridecodebin uri=<path>.mp4 ! glimagesink
```

If you find errors or warnings on the output related to hardware acceleration it may be due to a GStreamer bug. Remove the `gstreamer1.0-vaapi` package and it should work:

```console
apt-get remove gstreamer1.0-vaapi
```

## Examples 🌟

We provide some working applications under the `examples` directory, so you can easily run and play with them.

- [Cats face recognition](examples/cats)

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
