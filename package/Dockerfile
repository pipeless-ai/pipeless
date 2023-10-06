FROM bitnami/python:3.10.12

# Install gstreamer
RUN install_packages libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
    libgstreamer-plugins-bad1.0-dev gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly gstreamer1.0-libav gstreamer1.0-tools \
    gstreamer1.0-x gstreamer1.0-alsa gstreamer1.0-gl gstreamer1.0-gtk3 \
    gstreamer1.0-qt5 gstreamer1.0-pulseaudio

# Install required dependencies
RUN install_packages libcairo2-dev libgirepository1.0-dev

COPY scripts /

RUN /python-nonroot.sh

USER 1001

# Allow to execute commands installed with pip
ENV PATH="${PATH}:/.local/bin"

RUN pip install pipeless-ai[onnx-cpu] pipeless-ai-cli pipeless-ai-tf-models

WORKDIR /app

ENTRYPOINT ["/entrypoint.sh"]
