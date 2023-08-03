FROM bitnami/minideb:bullseye
RUN install_packages libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
    libgstreamer-plugins-bad1.0-dev gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly gstreamer1.0-libav gstreamer1.0-tools \
    gstreamer1.0-x gstreamer1.0-alsa gstreamer1.0-gl gstreamer1.0-gtk3 \
    gstreamer1.0-qt5 gstreamer1.0-pulseaudio

# Hack to allow mp4 files without errors. Note this library provides hardware acceleration, so we need an alternative fix.
# Test it by running this command: GST_DEBUG="*:3,GstVaapiPostproc:7,GstGLUploadElement:7" gst-launch-1.0 uridecodebin uri=<path>.mp4 ! glimagesink
RUN apt-get remove gstreamer1.0-vaapi
# Gstreamer python bindings
RUN install_packages python3-gi python3-gst-1.0

# Install poetry
RUN curl -sSL https://install.python-poetry.org | python3 -