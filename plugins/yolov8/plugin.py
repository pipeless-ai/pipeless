import os

import numpy as np
from ultralytics import YOLO
from ultralytics.utils.ops import scale_image
from pipeless_ai.lib.app.app import PipelessApp

class PipelessPlugin(PipelessApp):
    """
    Pipeless plugin to automatically load and execute YOLOv8 models.
    Using YOLO models you can perform image detection, segmentation, classification and pose estimation

    By installing this plugin your Pipeless application automatically
    executes the specified YOLO model for every frame and you can access the results from the application
    code under 'self.plugins.yolov8.[bounding_boxes,masks_data, masks_xyn,keypoints]' to your application.

    To change the default model use PIPELESS_PLUGIN_YOLOV8_MODEL.
    Note you need to provide them in the filename format and they will be automatically downloaded. Examples:
    * yolov8n.pt (default)
    * yolov8n-seg.pt
    * yolov8l-cls.pt
    * yolov8x-pose.pt
    Find all available models here: https://github.com/ultralytics/ultralytics#models
    """
    def __init__(self):
        model_to_load = os.environ.get('PIPELESS_PLUGIN_YOLOV8_MODEL', 'yolov8n.pt')
        self.model = YOLO(model_to_load)

    def process(self, frame):
        original_shape = frame.shape
        self.prediction = next(self.model(frame, stream=True)) # It returns an array because we can provide several images at once

        # Detection
        self.bounding_boxes = self.prediction.boxes.data.tolist() if self.prediction.boxes else []

        # Segmentation
        self.masks_data = self.prediction.masks.data.tolist() if self.prediction.masks else []
        self.masks_xyn = self.prediction.masks.xyn if self.prediction.masks else []
        if self.masks_data:
            # rescale masks to original image
            self.masks_data = np.moveaxis(self.masks_data, 0, -1) # masks, (H, W, N)
            self.masks_data = scale_image(self.masks_data, original_shape)
            self.masks_data = np.moveaxis(self.masks_data, -1, 0).tolist() # masks, (N, H, W)

        # Pose (keypoints)
        self.keypoints = self.prediction.keypoints.data.tolist() if self.prediction.keypoints else []
        if self.keypoints:
            self.keypoints = self.keypoints[0] # Remove one dimension

        return frame

    def label_from_number(self, number: int) -> str:
        return self.model.names.get(int(number))
