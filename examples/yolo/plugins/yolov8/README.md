# YOLOv8 Pipeless Plugin

Pipeless plugin to automatically load and execute YOLOv8 models. Using YOLO models you can perform image detection, segmentation and pose estimation out of the box.

By installing this plugin your Pipeless application will automatically execute the specified YOLO model on the `processing` hook for every frame.

The prediction results are exposed via the following variables in your Pipeless application:

* `self.plugins.yolov8.bounding_boxes`: Exposes predicted bounding boxes when using one of the detection models.
* `self.plugins.yolov8.masks_data`, `self.plugins.yolov8.masks_xyn`: Expose the calculated segmentation masks when using one of the segmentation models.
* `self.plugins.yolov8.keypoints`: Exposes the keypoints when using one of the pose estimation models.

## Configuration

The model is automatically downloaded when you run your Pipeless application. By default, the `yolov8n.pt` detection model is loaded. To change the default model simply export the `PIPELESS_PLUGIN_YOLOV8_MODEL` environment variable.

You need to provide the model with the filename notation, for example:

    * `yolov8n.pt` (default)
    * `yolov8n-seg.pt`
    * `yolov8l-cls.pt`
    * `yolov8x-pose.pt`

The whole list of available YOLOv8 models can be found [here](https://github.com/ultralytics/ultralytics#models)
