import numpy as np
import cv2

from pipeless_ai.lib.app.app import PipelessApp

def xywh2xyxy(i):
    o = i.view() # Create numpy view
    o[..., 0] = i[..., 0] - i[..., 2] / 2
    o[..., 1] = i[..., 1] - i[..., 3] / 2
    o[..., 2] = i[..., 0] + i[..., 2]
    o[..., 3] = i[..., 1] + i[..., 3]
    return o

def rescale_boxes(original_image_shape, model_input_shape, boxes):
    img_height, img_width, _ = original_image_shape
    input_height, input_width, _ = model_input_shape
    input_shape = np.array([input_width, input_height, input_width, input_height])
    boxes = np.divide(boxes, input_shape, dtype=np.float32)
    boxes *= np.array([img_width, img_height, img_width, img_height])
    return boxes

def process_output(model_output, orginal_image_shape, model_input_shape):
    confidence_threshold = 0.1
    iou_threshold = 0.5

    predictions = np.squeeze(model_output[0]).T

    scores = np.max(predictions[:, 4:], axis=1)
    predictions = predictions[scores > confidence_threshold, :]
    scores = scores[scores > confidence_threshold]
    if len(scores) == 0:
        return [], [], []

    class_ids = np.argmax(predictions[:, 4:], axis=1)

    # Extract boxes
    boxes = predictions[:, :4]
    boxes = rescale_boxes(orginal_image_shape, model_input_shape, boxes)
    boxes = xywh2xyxy(boxes)

    indices = cv2.dnn.NMSBoxes(boxes, scores, confidence_threshold, iou_threshold)
    return boxes[indices], scores[indices], class_ids[indices]

yolo_classes = ['person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat', 'traffic light',
               'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow',
               'elephant', 'bear', 'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
               'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard',
               'tennis racket', 'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
               'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
               'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote', 'keyboard',
               'cell phone', 'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'book', 'clock', 'vase',
               'scissors', 'teddy bear', 'hair drier', 'toothbrush']

class App(PipelessApp):
    def pre_process(self, frame):
        frame = cv2.normalize(frame, None, 0.0, 1.0, cv2.NORM_MINMAX)
        return  frame

    def post_process(self, frame):
        model_output = self.inference.results
        yolo_input_shape = (640, 640, 3)
        boxes, scores, class_ids = process_output(model_output, frame.shape, yolo_input_shape)
        assert len(boxes) == len(scores) == len(class_ids), "Boxes, scores and class_ids must have the same length"
        class_labels = [yolo_classes[id] for id in class_ids]
        color = (0, 255, 255)
        for i in range(len(boxes)):
            self.plugins.draw.boxes.append([*boxes[i], class_labels[i], scores[i], color])
        return frame
