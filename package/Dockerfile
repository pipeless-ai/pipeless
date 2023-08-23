FROM bitnami/python:3.10
RUN install_packages libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
    libgstreamer-plugins-bad1.0-dev gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly gstreamer1.0-libav gstreamer1.0-tools \
    gstreamer1.0-x gstreamer1.0-alsa gstreamer1.0-gl gstreamer1.0-gtk3 \
    gstreamer1.0-qt5 gstreamer1.0-pulseaudio

# Hack to allow mp4 files without errors. Note this library provides hardware acceleration, so we need an alternative fix.
#RUN apt-get remove gstreamer1.0-vaapi

RUN install_packages libcairo2-dev libgirepository1.0-dev

# Allow python to install packages as nonroot
RUN mkdir /.local && chmod g+w /.local
USER 1001
RUN pip install pipeless-ai pipeless-ai-cli
# Allow to execute commands installed with pip
ENV PATH="${PATH}:/.local/bin"

WORKDIR /app

ENTRYPOINT ["pipeless"]
