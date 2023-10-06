# Pipeless Helm Chart

This Helm Chart allows you to deploy Pipeless to a Kubernetes cluster.

It includes an RTMP server that allows you to send the input stream and read the output when enabled.

To deploy a sample application from the examples folder use the following command:

```bash
helm install pipeless . --set worker.application.git_repo="https://github.com/pipeless-ai/pipeless.git",worker.application.subPath="examples/onnx-yolo",worker.plugins.order="draw",worker.inference.model_uri="file:///app/yolov8n.onnx"
```

You can edit the command above for your custom application.

All the available parameters can be found at `Values.yaml`