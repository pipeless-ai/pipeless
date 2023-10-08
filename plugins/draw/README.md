# Pipeless plugin to automatically draw data over the frames

This plugin supports 3 types of input data:

* Bounding boxes
* Segmentation masks
* Keypoints

You can provide as many as you need at the same time for a single frame. Check the [input data](#input-data) section.

A usage example of this plugin can be found [here](https://pipeless.ai/docs/v0/examples/yolo).

## Configuration

This plugin accepts the following configuration env vars:

* `PIPELESS_PLUGIN_DRAW_CONFIDENCE_THRESHOLD`: Only apply to bounding boxes. The score threshold over which the data will be drawn. For example, if you set it to `0.85` only bounding boxes, masks or keypoints with a score higher than `0.85` will be drawn. By default, the confidence threshold is not applied and all the provided data is drawn.

## Input data

To pass data to this plugin you just need to set some variables in your Pipeless application.

> IMPORTANT: this plugin implements the `post-process` hook, thus, you must pass data before the `post-process` hook, i.e. during your `pre-process` or `process` hooks.

### Bounding Boxes

You can pass bounding boxes simply by setting `self.plugins.draw.boxes` in your Pipeless application.

It must be **an array** of boxes in format `[x1, y1, x2, y2, label, score, color]`. Where color must be an RGB tuple. Ex: `(128, 255, 0)`.

If you have the bounding boxes in format `[a, b, w, h]` simply apply the following conversion:
    * [x1, y1] = [a, b]
    * [x2, y2] = [a + width, b + height]

The `score` element is the detection score. It is used to filter results via a confidence threshold. Check the [configuration](#configuration) section to learn how to specify a confidence threshold. It can be set to `None` if you do not want to apply a confidence threshold.

### Segmentation masks

You can pass segmentation masks by setting `self.plugins.draw.masks` in your Pipeless application.

> IMPORTANT: If you provide segmentation masks **AND** bounding boxes, the plugin assumes each mask corresponds to the bounding box with the same index, and will draw it with the same color and apply the bounding box confidence score.

### Keypoints

You can pass keypoints by setting `self.plugins.draw.keypoints` in your Pipeless application.