# Multi-pose estimation example

In this example we will track the pose of a person during the video and print over the image the keypoints.
In this case, we make use of the `pipeless_ai_tf_models`, we don't even have to bring our own model, everything is ready to use.

## Requirements

* Pipeless modules: `pipeless_ai`, `pipeless_ai_cli` and `pipeless_ai_tf_models`
* OpenCV: `pip install opencv-python`

> NOTE: this directory includes a video you can use for testing

## Run the example

1. Clone the repo and install the pipeless framework as well as `pipeless_ai_tf_models`

1. Update `config.yaml` with the path you used to clone the repo (update the input and output video path). It **must** be an absolute path.

1. Move into the `pose` directory

1. Execute from the `pose` directory:

```console
pipeless run
```

You can now check the output video with any media player.

## Walkthrough

The first thing we need to do is to create an instance of out model. We do it into the `before` stage:
```python
def before(self):
    self.model = MultiPoseEstimationLightning()
```

Once we have an instance of our model, we can use it on every frame to get bounding boxes and keypoints:
```python
def process(self, frame):
    bboxes, keypoints = self.model.invoke_inference(frame)
```

Finally, we print our bounding boxes and keypoints into the original frame before returning it, so we can visualize the detections on the output:

```python
for bbox in bboxes:
    cv2.rectangle(frame, (bbox[1], bbox[0]), (bbox[3], bbox[2]), (0, 255, 0), 2)

for keypoint in keypoints:
    cv2.circle(frame, (keypoint[0], keypoint[1]), 5, (255, 0, 255), -1)

return frame
```

And that's all! Now execute `pipeless run` and open the output with any media player.