#from lightning import MultiPoseEstimationLightning
from pipeless_ai_tf_models.multi_pose_estimation.lightning import MultiPoseEstimationLightning

import cv2
import numpy as np

mpe = MultiPoseEstimationLightning()

rgb_image = cv2.imread('test.jpeg')
bboxes, keypoints = mpe.invoke_inference(rgb_image)

for bbox in bboxes:
    cv2.rectangle(rgb_image, (bbox[1], bbox[0]), (bbox[3], bbox[2]), (0, 255, 0), 2)

for keypoint in keypoints:
    cv2.circle(rgb_image, (keypoint[0], keypoint[1]), 5, (255, 0, 255), -1)

cv2.imshow('Annotated Image', rgb_image)
cv2.waitKey(0)
cv2.destroyAllWindows()