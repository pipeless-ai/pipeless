# Multi-pose estimation model

Input: RGB frame
Output:
* Bounding boxes array with detected persons
* Keypoints array with 17 keypoints: nose, left eye, right eye, left ear, right ear, left shoulder, right shoulder, left elbow, right elbow, left wrist, right wrist, left hip, right hip, left knee, right knee, left ankle, right ankle

# Usage example

```python
from pipeless_ai_tf_models.multi_pose_estimation.lightning import MultiPoseEstimationLightning
mpe = MultiPoseEstimationLightning()
bboxes, keypoints = mpe.invoke_inference(rgb_image)

# Print bounding boxes and keypoints over the image using OpenCV
for bbox in bboxes:
    cv2.rectangle(rgb_image, (bbox[1], bbox[0]), (bbox[3], bbox[2]), (0, 255, 0), 2)

for keypoint in keypoints:
    cv2.circle(rgb_image, (keypoint[0], keypoint[1]), 5, (255, 0, 255), -1)
```

> For a complete working example using Pipeless check [this](https://github.com/pipeless-ai/pipeless/tree/main/examples/pose)
