<p align="center">
  <a href="https://pipeless.ai">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="assets/pipeless-400x400-rounded.png">
      <img src="https://raw.githubusercontent.com/pipeless-ai/pipeless/main/assets/pipeless-400x400-rounded.png" height="128">
    </picture>
    <h1 align="center">Pipeless</h1>
  </a>
</p>

<p align="center">
  <a aria-label="Pipeless logo" href="https://pipeless.ai">
    <img src="https://img.shields.io/badge/MADE%20BY%20Pipeless%20ai-000000.svg?style=for-the-badge&logo=Pipeless&labelColor=000">
  </a>
  <a aria-label="Pipeless latest version" href="https://github.com/pipeless-ai/pipeless/releases">
    <img alt="" src="https://img.shields.io/github/v/release/pipeless-ai/pipeless?style=for-the-badge&label=latest&labelColor=000000">
  </a>
  <a aria-label="License" href="https://github.com/miguelaeh/pipeless/blob/main/LICENSE">
    <img alt="" src="https://img.shields.io/pypi/l/pipeless-ai?style=for-the-badge&labelColor=000000">
  </a>
  <a aria-label="Join the community on GitHub" href="https://github.com/miguelaeh/pipeless/discussions">
    <img alt="" src="https://img.shields.io/badge/Join%20the%20discussions-black.svg?style=for-the-badge&logo=&labelColor=000000&logoWidth=20">
  </a>
  <a aria-label="Join the community on Discord" href="https://discord.gg/K2qxQ8uedG">
    <img alt="" src="https://img.shields.io/discord/1156923628831649873?style=for-the-badge&logo=discord&logoColor=FFFFFF&label=Chat%20on%20discord&labelColor=black">
  </a>
</p>

<div align="center">
   <p><b>Easily create, deploy and run computer vision applications.</b></p>
   <br />

   <br />

   <div>
      <img width="382" align="center" alt="Loading video..." src="https://raw.githubusercontent.com/pipeless-ai/pipeless/main/assets/examples.gif">
   </div>

   <br /><br />
   <a href="https://agents.pipeless.ai">Check out our hosted agents solution</a>
</div>

**Pipeless is an open-source framework that takes care of everything you need to develop and deploy computer vision applications in just minutes.** That includes code parallelization, multimedia pipelines, memory management, model inference, multi-stream management, and more. Pipeless allows you to **ship applications that work in real-time in minutes instead of weeks/months**.

Pipeless is inspired by modern serverless technologies. You provide some functions and Pipeless takes care of executing them for new video frames and everything involved.

With Pipeless you create self-contained boxes that we call "stages". Each stage is a micro pipeline that performs a specific task. Then, you can combine stages dynamically per stream, allowing you to process each stream with a different pipeline without changing your code and without restarting the program. To create a stage you simply provide a pre-process function, a model and a post-process function.

You can load **industry-standard models**, such as YOLO, **or custom models** in one of the supported inference runtimes just by providing a URL. Pipeless ships some of the most popular inference runtimes, such as the ONNX Runtime, allowing you to run inference with high performance on CPU or GPU out-of-the-box.

You can deploy your Pipeless and your applications to edge and IoT devices or to the cloud. There are several tools for the deployment, including container images.

The following is a **non-exhaustive** set of relevant features that Pipeless includes:

* **Multi-stream support**: process several streams at the same time.
* **Dynamic stream configuration**: add, edit, and remove streams on the fly via a CLI or REST API (more adapters to come).
* **Multi-language support**: you can Write your hooks in several languages, including Python.
* **Dynamic processing steps**: you can add any number of steps to your stream processing, and even modify those steps dynamically on a per-stream basis.
* **Built-in restart policies**: Forget about dealing with connection errors, cameras that fail, etc. You can easily specify restart policies per stream that handle those situations automatially.
* **Highly parallelized**: do not worry about multi-threading and/or multi-processing, Pipeless takes care of that for you.
* **Several inference runtimes supported**: Provide a model and select one of the supported inference runtimes to run it out-of-the-box in CPU or GPUs. We support **CUDA**, **TensorRT**, **OpenVINO**, **CoreML**, and more to come.
* **Well-defined project structure and highly reusable code**: Pipeless uses the file system structure to load processing stages and hooks, helping you organize the code in highly reusable boxes. Each stage is a directory, each hook is defined on its own file.

**<a href="https://www.pipeless.ai/docs/docs/v1/getting-started#create-a-new-project">Get started now!</a>**

**Join our [community](https://discord.gg/K2qxQ8uedG) and contribute to making the lives of computer vision developers easier!**

## Requirements ☝️

* **Python**. Pre-built binaries are linked to Python 3.10 in Linux amd64, 3.8 in Linux arm64, and 3.12 in macOS. If you have a different Python version, provide the `--build` flag to the install script to build from source so Pipeless links to your installed Python version (or update your version and use a pre-built binary, which is simpler).
* **Gstreamer 1.20.3**. Verify with `gst-launch-1.0 --gst-version`. Installation instructions [here](https://gstreamer.freedesktop.org/documentation/installing/index.html?gi-language=python)

## Installation 🛠️

```console
curl https://raw.githubusercontent.com/pipeless-ai/pipeless/main/install.sh | bash
```

Find more information and installation options [here](https://www.pipeless.ai/docs/v1/getting-started/installation).

### Using docker

Instead of installing locally, you can alternatively use docker and save the time of installing dependencies:

```console
docker run miguelaeh/pipeless --help
```

To use it with CUDA:

```console
docker run miguelaeh/pipeless:latest-cuda --help
```

To use with TensorRT use:

```console
docker run miguelaeh/pipeless:latest-tensorrt --help
```

Find the whole container documentation [here](https://www.pipeless.ai/docs/v1/container).

## Getting Started 🚀

Init a project:

```console
pipeless init my_project --template scaffold
cd my_project
```

Start Pipeless:

```console
pipeless start --stages-dir .
```

Provide a stream:

```console
pipeless add stream --input-uri "https://pipeless-public.s3.eu-west-3.amazonaws.com/cats.mp4" --output-uri "screen" --frame-path "my-stage"
```

The code generated is an empty template that scafold a stage so it will do nothing. Please go to the [examples](https://www.pipeless.ai/docs/v1/examples) to complete that stage.

You can also use the interactive shell to create the project:

<img width="382" align="center" alt="Loading video..." src="https://raw.githubusercontent.com/pipeless-ai/pipeless/main/assets/interactive_shell.gif" />

Check the complete [getting started guide](https://pipeless.ai/docs/v1/getting-started) or plunge into the [complete documentation](https://www.pipeless.ai/docs).

## Examples 🌟

You can find some examples under the `examples` directory. Just copy those folders inside your project and play with them.

Find [here](https://pipeless.ai/docs/v1/examples) the whole list of examples and step by step guides.

## Benchmark 📈

We deployed Pipeless to several different devices so you can have a general idea of its performance. Find the results at the [benchmark section](https://pipeless.ai/docs/v1/benchmark) of the docs.

## Notable Changes

Notable changes indicate important changes between versions. Please check the [whole list of notable changes](https://pipeless.ai/docs/v1/changes).

## Contributing 🤝

Thanks for your interest in contributing! Contributions are welcome and encouraged. While we're working on creating detailed contributing guidelines, here are a few general steps to get started:

1. Fork this repository.
2. Create a new branch: `git checkout -b feature-branch`.
3. Make your changes and commit them: `git commit -m 'Add new feature'`.
4. Push your changes to your fork: `git push origin feature-branch`.
5. Open a GitHub **pull request** describing your changes.

We appreciate your help in making this project better!

Please note that for major changes or new features, it's a good idea to discuss them in an issue first so we can coordinate efforts.

## License 📄

This project is licensed under the [Apache License 2.0](LICENSE).

### Apache License 2.0 Summary

The Apache License 2.0 is a permissive open-source license that allows you to use, modify, and distribute this software for personal or commercial purposes. It comes with certain obligations, including providing attribution to the original authors and including the original license text in your distributions.

For the full license text, please refer to the [Apache License 2.0](LICENSE).
