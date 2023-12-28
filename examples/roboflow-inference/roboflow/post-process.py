import cv2

def hook(frame_data, _):
    predictions = frame_data["inference_output"]
    for pred in predictions:
        x, y, width, height, confidence, class_label = pred.values()
        x, y, width, height = int(x), int(y), int(width), int(height)
        cv2.rectangle(frame_data["original"], (x, y), (x + width, y + height), (0, 255, 0), 1)
