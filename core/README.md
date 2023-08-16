# Pipeless Core

The Pipeless core is split into several components:

* `input`: Receives the media streams, demux and decode the streams.
* `worker`: Receives raw media frames, either audio or video frames, and processes them according to the user provided app
* `output`: Receives the processed raw media frames, encodes and mux them into the proper container format for the output protocol provided by the user

# System Dependencies

* **Gstreamer 1.20.3**. Verify with `gst-launch-1.0 --gst-version`. Installation instructions [here](https://gstreamer.freedesktop.org/documentation/installing/index.html?gi-language=python)

# Development

To test your changes run the following command from the `src` directory:

```console
python -m pipeless.pipeless <component> [app_path]
```

* `<component>` can be `input`, `worker`, `output`, `all` (default)
* `app_path` is required for `worker` component and must be the path to the `app.py` (including `app.py`)

For simplicity, it will load a mock configuration (hardcoded) at `src/pipeless/pipeless.py` that you can edit for your use case.
The hardcoded configuration will only be used when launching the components with the command above, it won't affect if testing with the CLI.

In order to debug, you can set the configuration `log_level` to `DEBUG`.
If you find an error related to GStreamer and no usefull information has been logged, try using the env var `GST_DEBUG=5` to enable GStreamer debug logs. Refer to this [page](https://gstreamer.freedesktop.org/documentation/tutorials/basic/debugging-tools.html?gi-language=python) for more information about GStreamer debugging.