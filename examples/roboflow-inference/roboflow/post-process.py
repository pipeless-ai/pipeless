import cv2

def hook(frame_data, _):
    predictions = frame_data["inference_output"]
    for pred in predictions:
        x = pred.get_x()
        y = pred.get_y()
        width = pred.get_width()
        height = pred.get_height()
        confidence = pred.get_confidence()
        pred_class = pred.get_class()
        class_id = pred.get_class_id()
        class_confidence = pred.get_class_confidence()

        print("Detected bounding box:", x, y, width, height, class_confidence)
        points = pred.get_points()
        for point in points:
            print("Segmentation point:",point.get_x(), point.get_y())
        x, y, width, height = int(x), int(y), int(width), int(height)

        # Draw bbox
        cv2.rectangle(frame_data["modified"], (x, y), (x + width, y + height), (0, 255, 0), 1)
