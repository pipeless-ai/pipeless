from pipeless_ai.lib.app.app import PipelessApp
from pipeless_ai_tf_models.multi_pose_estimation.lightning import MultiPoseEstimationLightning

import cv2

class App(PipelessApp):
    def before(self, ctx):
        ctx['model'] = MultiPoseEstimationLightning()

    def process(self, frame, ctx):
        model = ctx['model']
        bboxes, keypoints = model.invoke_inference(frame)

        for bbox in bboxes:
            cv2.rectangle(frame, (bbox[1], bbox[0]), (bbox[3], bbox[2]), (0, 255, 0), 2)

        for keypoint in keypoints:
            cv2.circle(frame, (keypoint[0], keypoint[1]), 5, (255, 0, 255), -1)

        return frame

