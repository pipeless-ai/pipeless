import cv2
import numpy as np

def hook(frame_data, _):
    frame = frame_data['original']
    model_output = frame_data['inference_output']
    yolo_input_shape = (640, 640, 3) # h,w,c
    boxes, scores, class_ids = parse_yolo_output(model_output, frame.shape, yolo_input_shape)
    class_labels = [yolo_classes[id] for id in class_ids]
    for i in range(len(boxes)):
        draw_bbox(frame, boxes[i], class_labels[i], scores[i])

    frame_data['modified'] = frame

#################################################
# Util functions to make the hook more readable #
#################################################
yolo_classes = ['person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat', 'traffic light',
               'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow',
               'elephant', 'bear', 'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
               'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard',
               'tennis racket', 'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
               'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
               'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote', 'keyboard',
               'cell phone', 'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'book', 'clock', 'vase',
               'scissors', 'teddy bear', 'hair drier', 'toothbrush']

def xywh2xyxy(i):
    o = i.view() # Create numpy view
    dw = i[..., 2] / 2
    dh = i[..., 3] / 2
    o[..., 0] = i[..., 0] - dw
    o[..., 1] = i[..., 1] - dh
    o[..., 2] = i[..., 0] + dw
    o[..., 3] = i[..., 1] + dh
    return o

def rescale_boxes(original_image_shape, model_input_shape, boxes):
    img_height, img_width, _ = original_image_shape
    input_height, input_width, _ = model_input_shape
    input_shape = np.array([input_width, input_height, input_width, input_height])
    boxes = np.divide(boxes, input_shape, dtype=np.float32)
    boxes *= np.array([img_width, img_height, img_width, img_height])
    return boxes

def parse_yolo_output(model_output, orginal_image_shape, model_input_shape):
    confidence_threshold = 0.3
    iou_threshold = 0.7

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

def clip_boxes(boxes, shape):
    boxes[..., [0, 2]] = boxes[..., [0, 2]].clip(0, shape[1])  # x1, x2
    boxes[..., [1, 3]] = boxes[..., [1, 3]].clip(0, shape[0])  # y1, y2

def draw_bbox(image, box, label='', score=None, color=(255, 0, 255), txt_color=(255, 255, 255)):
    lw = max(round(sum(image.shape) / 2 * 0.003), 2)
    p1, p2 = (int(box[0]), int(box[1])), (int(box[2]), int(box[3]))
    cv2.rectangle(image, p1, p2, color, thickness=lw, lineType=cv2.LINE_AA)
    if label:
        tf = max(lw - 1, 1)  # font thickness
        w, h = cv2.getTextSize(str(label), 0, fontScale=lw / 3, thickness=tf)[0]  # text width, height
        outside = p1[1] - h >= 3
        p2 = p1[0] + w, p1[1] - h - 3 if outside else p1[1] + h + 3
        cv2.rectangle(image, p1, p2, color, -1, cv2.LINE_AA)  # filled
        if score is not None:
            cv2.putText(image, f'{label} - {score}', (p1[0], p1[1] - 2 if outside else p1[1] + h + 2),
                0, lw / 3, txt_color, thickness=tf, lineType=cv2.LINE_AA)
        else:
            cv2.putText(image, label, (p1[0], p1[1] - 2 if outside else p1[1] + h + 2),
                0, lw / 3, txt_color, thickness=tf, lineType=cv2.LINE_AA)
