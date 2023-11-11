<p align="center">
  <a href="https://pipeless.ai">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="assets/pipeless-400x400-rounded.png">
      <img src="assets/pipeless-400x400-rounded.png" height="128">
    </picture>
    <h1 align="center">Pipeless</h1>
    <p>Easily create, deploy and run computer vision applications.</p>
  </a>
</p>

<p align="center">
  <a aria-label="Pipeless logo" href="https://pipeless.ai">
    <img src="https://img.shields.io/badge/MADE%20BY%20Pipeless%20ai-000000.svg?style=for-the-badge&logo=Pipeless&labelColor=000">
  </a>
  <a aria-label="Python version" href="https://pypi.org/project/pipeless-ai/">
    <img alt="" src="https://img.shields.io/pypi/v/pipeless-ai?style=for-the-badge&label=PyPi&labelColor=000000">
  </a>
  <a aria-label="License" href="https://github.com/miguelaeh/pipeless/blob/main/license.md">
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
   <p>Pipeless is an open-source computer vision framework to create and deploy applications that analyze and manipulate video streams in real-time without the complexity of building and maintaining multimedia pipelines.</p>
   <p>Join our community and contribute to make the life of computer vision developers easier!</p>

   <br />

   <div>
      <img height="350" align="center" src="assets/pipeless-yolo.gif">
   </div>

   <br /><br />
</div>

Pipeless ships all the features you need to create and deploy efficient computer vision applications that work in real-time.

Pipeless is inspired by modern serverless technologies to allow you write code in any language and that runs anywhere, including edge and IoT devices. Just like you implement small independent functions that react to http events for serverless web applications, with Pipeless you write functions that react to events on video frames.

You can easily use industry-standard models such as YOLO, or bring your own custom model and load it in one of the supported inference runtimes for high performance. Pipeless ships some of the most popular inference runtimes embedded, such as the ONNX Runtime, allowing you to run inference using any compatible model in CPUs and GPUs out-of-the-box.

You can deploy Pipeless into edge and IoT devices or to the cloud. We provide several tools for the deployment, including container images and Kubernetes Helm Charts.

## Requirements ☝️

* Python (tested with version `3.10.12`)
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

Check the complete [getting started guide](https://pipeless.ai/docs/v1/getting-started) or plunge into the [complete documentation](https://www.pipeless.ai/docs).

## Examples 🌟

You can find some examples under the `examples` directory. Just copy those folders inside your project and play with them.

Find [here](https://pipeless.ai/docs/v1/examples) the whole list of examples and step by step guides.

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
