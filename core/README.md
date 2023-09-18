# Pipeless Core

[Pipeless](https://www.pipeless.ai) is a computer vision framework to quickly create and deploy applications that process real time streams. Pipeless Core is the core component of the framework.

The Pipeless core is split into several components:

* `input`: Receives the media streams, demux and decode the streams.
* `worker`: Receives raw media frames, either audio or video frames, and processes them according to the user provided app
* `output`: Receives the processed raw media frames, encodes and mux them into the proper container format for the output protocol provided by the user

## System Dependencies

* **Gstreamer 1.20.3**. Verify with `gst-launch-1.0 --gst-version`. Installation instructions [here](https://gstreamer.freedesktop.org/documentation/installing/index.html?gi-language=python)

## Python dependencies

* Poetry: find the installation instructions [here](https://python-poetry.org/docs/#installation)

## Installation

```console
pip install pipeless-ai
```

## Development

To test your changes run the following command from the project root directory:

```console
python -m pipeless_ai.core <component> [app_file_path.py]
```

* `<component>` can be `input`, `worker`, `output`, `all` (default)
* `app_path` is required for `worker` component and must be the path to the `app.py` (including `app.py`)

For simplicity, it will load a mock configuration (hardcoded) at `src/pipeless/pipeless.py` that you can edit for your use case.
The hardcoded configuration will only be used when launching the components with the command above, it won't affect if testing with the CLI.

In order to debug, you can set the configuration `log_level` to `DEBUG`.
If you find an error related to GStreamer and no usefull information has been logged, try using the env var `GST_DEBUG=5` to enable GStreamer debug logs. Refer to this [page](https://gstreamer.freedesktop.org/documentation/tutorials/basic/debugging-tools.html?gi-language=python) for more information about GStreamer debugging.

## Manual Testing

In order to test your changes, start the virtualenv:

```console
poetry shell
```

After that, go to the `cli` directory and run `poetry install` to install the `pipeless-ai-cli` (CLI) component.
Then go to the `core` directory and run `poetry install` to install the `pipeless-ai` module. This will override the upstream dependency from the CLi componet to use your local one.

Verify you environment by ensuring the pipeless modules are pointing to your local directories instead of the PyPi public modules:

```console
pip list | grep pipeless
```

With that, you should be able to run `pipeless run` with your changes.