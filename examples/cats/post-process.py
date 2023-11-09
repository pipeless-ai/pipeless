import cv2

def hook(frame_data, _):
    frame = frame_data['original']
    original_height, original_width, _ = frame.shape
    reduced_height, reduced_width, _ = frame_data['modified'].shape
    bounding_boxes = frame_data['inference_output']

    # Draw the bounding boxes over the original frame
    for box in bounding_boxes:
        a, b, width, height = box
        # Recalculate bounding box for the original image
        a = int(a * (original_width / reduced_width))
        b = int(b * (original_height / reduced_height))
        width = int(width * (original_width / reduced_width))
        height = int(height * (original_height / reduced_height))
        cv2.rectangle(frame, (a, b), (a + width, b + height), (255, 0, 255), 2)

    frame_data['modified'] = frame
