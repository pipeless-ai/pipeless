import cv2

def hook(frame_data, _):
    frame = frame_data['modified']
    bboxes = frame_data.get('inference_output', [])
    for box in bboxes:
        x1, y1, x2, y2, score, class_number = box
        box_label(frame, [x1, y1, x2, y2], yolo_classes[int(class_number)], score, (255, 0, 255))

    bboxes = bboxes.tolist()
    # Add the predictions to the frame user_data in order to recover it frm other stages
    frame_data['user_data'] = {
        "bboxes": [bbox[:4] for bbox in bboxes],
        "scores": [bbox[4] for bbox in bboxes],
        "labels": [yolo_classes[int(bbox[5])] for bbox in bboxes]
    }

    frame_data['modified'] = frame

# Classes defined in the YOLO model to obtain the predicted class label
yolo_classes = ['person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat', 'traffic light',
               'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow',
               'elephant', 'bear', 'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
               'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard',
               'tennis racket', 'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
               'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
               'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote', 'keyboard',
               'cell phone', 'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'book', 'clock', 'vase',
               'scissors', 'teddy bear', 'hair drier', 'toothbrush']

# Prints a box with a label over the image
def box_label(image, box, label='', score=None, color=(255, 0, 255), txt_color=(255, 255, 255)):
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
