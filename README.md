# Pupila

A framework to build and deploy computer multimodal perception applications in minutes.

Just focus on your models (or take a pre-trained one), Pupila handles all the multimedia side.

# Requirements

* **Gstreamer 1.20.3**. Verify with `gst-launch-1.0 --gst-version`. Installation instructions [here](https://gstreamer.freedesktop.org/documentation/installing/index.html?gi-language=python)

You can use the provided Docker image which contains an already working environment

# Installation

```console
pip install pupila-cli
```

# Usage

## Create a new project

Run the following command:

```console
pupila-cli create project <project-name>
```

By default, the above command will use an empty project template. You need to implement some functionality on it.

## Project structure

The `create project` command will create a directory under your project name with the following files:

* `app.py`: contains your `App` class. This file contains the implementation of your processing functions. For example, throwing inference on a CV model. Inot this file you will define the functions in charge of procesing the media frames.

* `config.yaml`: contains the configuration of the framework components. You can also override all configuration options via env vars starting with `PUPILA_` followed by the config option name in capital letters.

## Media Processing

The processing steps are defined as methods of the `App` class. There are several processing stages that you can override:

* Initial and final stages

These are represented by methods that are executed just once per stream.

They are tipically used when your app requires to execute some code before starting the processing or once the stream processing ends.

- `before`: contains code that is executed before processing any content from a stream
- `after`: contains code that is executed after the processing of a whole stream.

* Processing stages

These are the stages that actually modify/learn/process the media streams. All of them receive a frame and **must** return a frame. The frames can be of any type(audio, video, text, metadata, ...).

- `pre_process`: code to execute to prepare a frame to be processed
- `process`: code for the actual frame processing
- `post-process`: code to execute after a frame is processed

These stages have been mainly defined for a proper logical code structure, there are no significant differences on how the code is executed on them.

* Context

You app can maintain its own internal state. This is useful when you need to pass information between stages.

By default, an internal context is created and can be accessed via the `ctx` variable.

You can also define your own variables within the `App` class, however, note that if you override the constructor the context won't be initialized properly.

## Configuration

To configure your app you can use either env vars or the config file (`config.yaml`).

| Option | Description | Value(s)/Type |
| ------ | ----------- | -------- |
| `log_level` | Level of the logging|  `DEBUG`, `INFO`, `WARN`, `ERROR` |
| `n_workers` | Number of workers deployed | int |
| `input.address.host` | Host where the input component is running | `localhost` (string) |
| `input.address.port` | Port of the input component process | `1234` (int) |
| `input.video.enable` | Whether to enable to video input | `true` (boolean) |
| `input.video.uri`    | Uri of the input video to process. Must include the protocol (`file://`, `https://`, `rtmp://`, etc) | string |
| `output.address.host` | Host where the output component is running | `localhost` (string) |
| `output.address.port` | Port of the output component process | `1234` (int) |
| `output.video.enable` | Whether to enable to video output | `true` (boolean) |
| `output.video.uri`    | Uri where to send the processed output video. Must include the protocol (`file://`, `https://`, `rtmp://`, etc) | string |

## Run your app

To test your app execute the following from your app directory:

```console
pupila-cli run <component>
```

`<component>` must be one of `input`, `worker`, `output`, `all` (default).

When running your application locally, simply use `all` and everything will run automatically on the proper order.

### Core Components

Pupila has been designed for easy local execution but more important, to easily deploy to the cloud. Thus, it is split in 3 main components:

* `input`: Receives the media streams, demux and decode the streams.
* `worker`: Receives raw media frames, and processes them according to the user app. You can deploy any number of workers and the processing will be load balanced automatically using a round robin schedule. When deployed to the cloud this allows to reach **real time** processing even with each frame takes relatively long times to process. Note in that case, that each worker executes the `before` and `after` stages and that each worker has a different instance of the running app context.
* `output`: Receives the processed raw media frames, encodes and mux them into the proper container format for the output protocol provided by the user

Each component runs with independence of the others.

# Current state

Pupila is in an alpha state. Below you can find the fields currently supported as well as the formats and protocols.

* Computer vision / video processing

| Input Protocol | Input Format  |
| -------------- | ------------- |
| `file`, `http`, `rtmp`, `rtsp` | `mp4` |

| Output Protocol | Output Format
| ------------- | ------------- | ------------------------------------------- |
| `screen`      | `raw` (Directly shown on the device screen) |
| `file`        | `mp4`         |

* Audio recognition / audio processing (in progress)

# Known issues

* If the pipeline doesn't start and there is not apparent error even on the debug logs run the following command changing `<path>` by your file path:

```console
GST_DEBUG="*:3,GstVaapiPostproc:7,GstGLUploadElement:7" gst-launch-1.0 uridecodebin uri=<path>.mp4 ! glimagesink
```

If you find errors or warnings on the output related to hardware acceleration it may be due to a GStreamer bug. Remove the `gstreamer1.0-vaapi` package and it should work:

```console
apt-get remove gstreamer1.0-vaapi
```