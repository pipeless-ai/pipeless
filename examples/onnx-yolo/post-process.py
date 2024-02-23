import cv2
import numpy as np

def hook(frame_data, _):
    frame = frame_data['original']
    model_output = frame_data['inference_output']
    if len(model_output) > 0:
        yolo_input_shape = (640, 640, 3) # h,w,c
        boxes, scores, class_ids = postprocess_yolo(frame.shape, yolo_input_shape, model_output.get("output0", []))
        class_labels = [yolo_classes[id] for id in class_ids]
        for i in range(len(boxes)):
            draw_bbox(frame, boxes[i], class_labels[i], scores[i], color_palette[class_ids[i]])

        frame_data['modified'] = frame

#################################################
# Util functions to make the hook more readable #
#################################################
confidence_thres = 0.45
iou_thres = 0.5

yolo_classes = ['person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat', 'traffic light',
               'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow',
               'elephant', 'bear', 'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
               'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard',
               'tennis racket', 'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
               'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
               'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote', 'keyboard',
               'cell phone', 'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'book', 'clock', 'vase',
               'scissors', 'teddy bear', 'hair drier', 'toothbrush']
color_palette = np.random.uniform(0, 255, size=(len(yolo_classes), 3))

def xywh2xyxy(i):
    """
    Converts from (center-x, center-y,w,h) to (x1,y1,x2,y2)
    """
    o = i.view() # Create numpy view
    o[..., 0] = i[..., 0] - i[..., 2] / 2
    o[..., 1] = i[..., 1] - i[..., 3] / 2
    o[..., 2] = i[..., 0] + i[..., 2]
    o[..., 3] = i[..., 1] + i[..., 3]
    return o

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

def postprocess_yolo(original_frame_shape, resized_img_shape, output):
    original_height, original_width, _ = original_frame_shape
    resized_height, resized_width, _ = resized_img_shape

    outputs = np.transpose(np.squeeze(output[0]))

    # Get the number of rows in the outputs array
    rows = outputs.shape[0]

    boxes = []
    scores = []
    class_ids = []

    # Calculate the scaling factors for the bounding box coordinates
    if original_height > original_width:
        scale_factor = original_height / resized_height
    else:
        scale_factor = original_width / resized_width

    # Iterate over each row in the outputs array
    for i in range(rows):
        classes_scores = outputs[i][4:]

        # FIXME: For some reason when using YOLO in ONNX sometimes it returns NaN values in the classes scores
        #        and other times it returns 1 for some classes and 0 for the rest which is almost certainly a bad prediction.
        #        This hack skips those entries
        nan_mask = np.isnan(classes_scores)
        if np.any(nan_mask):
            continue
        if np.any(classes_scores == 1):
            continue

        max_score = np.amax(classes_scores)
        if max_score >= confidence_thres:
            class_id = np.argmax(classes_scores) # Get the class ID with the highest score
            x, y, w, h = outputs[i][0], outputs[i][1], outputs[i][2], outputs[i][3]

            ## Calculate the scaled coordinates of the bounding box
            ## the original image was padded to be square
            if original_height > original_width:
                # we added pad on the width
                pad = (resized_width - original_width / scale_factor) // 2
                left = int((x - pad) * scale_factor)
                top = int(y * scale_factor)
            else:
                # we added pad on the height
                pad = (resized_height - original_height / scale_factor) // 2
                left = int(x * scale_factor)
                top = int((y - pad) * scale_factor)
            width = int(w * scale_factor)
            height = int(h * scale_factor)

            class_ids.append(class_id)
            scores.append(max_score)
            boxes.append([left, top, width, height])

    if len(boxes) > 0:
        boxes = np.array(boxes)
        scores = np.array(scores)
        class_ids = np.array(class_ids)

        clip_boxes(boxes, original_frame_shape)
        boxes = xywh2xyxy(boxes)
        indices = cv2.dnn.NMSBoxes(boxes, scores, confidence_thres, iou_thres)

        return boxes[indices], scores[indices], class_ids[indices]
    else:
        return [], [], []
