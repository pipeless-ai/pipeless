# make stateful

from norfair import Detection, draw_points
import numpy as np

def hook(frame_data, context):
    tracker = context['tracker']
    frame = frame_data['modified']
    bboxes, scores, labels = frame_data['user_data'].values()
    norfair_detections = yolo_to_norfair(bboxes, scores)
    tracked_objects = tracker.update(detections=norfair_detections)
    draw_points(frame, drawables=tracked_objects)
    frame_data['modified'] = frame

def yolo_to_norfair(bboxes, scores):
    norfair_detections = []
    for i, bbox in enumerate(bboxes):
        box_corners = [[bbox[0], bbox[1]], [bbox[2], bbox[3]]]
        box_corners = np.array(box_corners)
        corners_scores = np.array([scores[i], scores[i]])
        norfair_detections.append(Detection(points=box_corners, scores=corners_scores))

    return norfair_detections
