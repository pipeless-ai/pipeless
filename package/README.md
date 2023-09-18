# Pipeless container library

This directory contains the source files to build the Pipeless container images.

The container images provide a way to run Pipeless out-of-the box without having to deal with dependencies.


## Using the CUDA image

You need to install the Nvidia Container Toolkit to use the CUDA images. run with `--gpus all` option.

```console
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
  && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list \
  && \
    sudo apt-get update
```

then reload the docker daemon to take the toolkit into account:

```console
systemctl restart docker
```

Finally, provide the `--gpus all` option to your `docker` command.

## Image Usage

Print help command:

```console
docker run --rm miguelaeh/pipeless --help
```

Create a new project locally:

```console
docker run --rm -v /your/app/dir:/app miguelaeh/pipeless create project my_app_name
```

Run all components:

```console
docker run --rm -v /your/app/dir:/app miguelaeh/pipeless run all
```

Run input only:

```console
docker run --rm miguelaeh/pipeless run input
```

### Install Custom Python Packages

Sometimes, your app may require python packages that are not installed by default into the pipeless container. You can use the `PIPELESS_USER_PYTHON_PACKAGES` variable to automatically install them on start. You can specify them as a list separated by commas (`,`), semicolons (`;`) or spaces (` `). For example:

```console
docker run --rm -e "PIPELESS_USER_PYTHON_PACKAGES=opencv-python;some_other_package" miguelaeh/pipeless run worker
```

### Important Notes

If you want to store the processed media to a file, it must be done in a path under `/app`. For example, setting `PIPELESS_OUTPUT_VIDEO_URI=file:///app/my_video.mp4`.
Futhermore, the directory mounted at `/app` (i.e. `/your/app/dir` on the above examples) must have group `root` with write permissions.

## Docker compose usage

The `docker-compose.yaml` file allows you to automatically deploy your application locally as if it would be deployed to the cloud.

Start docker compose:

```console
APP_DIR=/your/app/dir docker compose up
```

Stop the docker compose:

```console
APP_DIR=/your/app/dir docker compose down -v
```
