# Pupila

An open source framework to easily build and deploy production computer vision and multimedia applications in minutes.

# Requirements

* **Gstreamer 1.20.3**. Verify with `gst-launch-1.0 --gst-version`. Installation instructions [here](https://gstreamer.freedesktop.org/documentation/installing/index.html?gi-language=python)

# Development

Start the application by running:

```console
python -m src.pupila.pupila <component>
```

`<component>` can be `input`, `worker`, `output`, `all` (default)

It will load a mock configuration (hardcoded) at `src/pupila/pupila.py`.
That configuraion will only be used when launchin the components with the command above. It is intended to be easily editable for development.
On the same file, you can change the component to run by passing it as argument: `input`, `worker`, `output` or `all` (default).

In order to debug, you can set the configuration `log_level` to `DEBUG`.
If you find an error related to GStreamer and no usefull information has been logged, try using the env var `GST_DEBUG=5` to enable GStreamer debug logs.

# Known issues

* The `poetry` environment is not able to recognise the GStreamer overrides producing errors like the following:
```
TypeError: Gst.Bin.add() takes exactly 2 arguments (4 given)
```

* If the pipeline doesn't start and there is not apparent error even on the debug logs run the following command changing `<path>` by your file path:

```console
GST_DEBUG="*:3,GstVaapiPostproc:7,GstGLUploadElement:7" gst-launch-1.0 uridecodebin uri=<path>.mp4 ! glimagesink
```

If you find errors or warnings on the output related to hardware acceleration it may be due to a GStreamer bug. Remove the `gstreamer1.0-vaapi` package and it should work:

```console
apt-get remove gstreamer1.0-vaapi
```