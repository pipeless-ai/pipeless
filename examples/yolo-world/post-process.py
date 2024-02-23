import cv2
import numpy as np

def hook(frame_data, _):
    frame = frame_data['original']
    model_output = frame_data['inference_output']
    if len(model_output) > 0:
        yolo_input_shape = (640, 640, 3) # h,w,c
        boxes, scores, class_ids = postprocess_yolo_world(frame.shape, yolo_input_shape, model_output)
        class_labels = [yolo_classes[int(id)] for id in class_ids]
        for i in range(len(boxes)):
            draw_bbox(frame, boxes[i], class_labels[i], scores[i], color_palette[int(class_ids[i])])

        frame_data['modified'] = frame

#################################################
# Util functions to make the hook more readable #
#################################################
yolo_classes = ['hard hat', 'gloves', 'protective boot', 'reflective vest', 'person']
color_palette = np.random.uniform(0, 255, size=(len(yolo_classes), 3))

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

def postprocess_yolo_world(original_frame_shape, resized_img_shape, output):
    original_height, original_width, _ = original_frame_shape
    resized_height, resized_width, _ = resized_img_shape

    boxes = np.array(output['boxes'][0])
    classes = np.array(output['labels'][0])
    scores = np.array(output['scores'][0])

    # Filter negative indexes
    neg_indexes_classes = np.where(classes < 0)[0]
    neg_indexes_scores = np.where(scores < 0)[0]
    neg_indexes = np.concatenate((neg_indexes_classes, neg_indexes_scores))

    mask = np.ones(classes.shape, dtype=bool)
    mask[neg_indexes] = False

    boxes = boxes[mask]
    classes = classes[mask]
    scores = scores[mask]

    # arrays to accumulate the results
    result_boxes = []
    result_classes = []
    result_scores = []

    # Calculate the scaling factors for the bounding box coordinates
    if original_height > original_width:
        scale_factor = original_height / resized_height
    else:
        scale_factor = original_width / resized_width

    # Resize the output boxes
    for i, score in enumerate(scores):
        if score < 0.05: # apply confidence threshold
            continue
        if not score < 1:
            continue # Remove bad predictions that return a score of 1.0

        x1, y1, x2, y2 = boxes[i][0], boxes[i][1], boxes[i][2], boxes[i][3]

        ## Calculate the scaled coordinates of the bounding box
        ## the original image was padded to be square
        if original_height > original_width:
            # we added pad on the width
            pad = (resized_width - original_width / scale_factor) // 2
            x1 = int((x1 - pad) * scale_factor)
            y1 = int(y1 * scale_factor)
            x2 = int((x2 - pad) * scale_factor)
            y2 = int(y2 * scale_factor)
        else:
            # we added pad on the height
            pad = (resized_height - original_height / scale_factor) // 2
            x1 = int(x1 * scale_factor)
            y1 = int((y1 - pad) * scale_factor)
            x2 = int(x2 * scale_factor)
            y2 = int((y2 - pad) * scale_factor)

        result_classes.append(classes[i])
        result_scores.append(score)
        result_boxes.append([x1, y1, x2, y2])

    return result_boxes, result_scores, result_classes
