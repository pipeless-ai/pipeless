import cv2

def hook(frame, context):
    model = context['model']

    frame_arr = frame['modified']
    # Create reduced frame for faster detection
    original_height, original_width, _ = frame_arr.shape
    aspect_ratio = original_width / original_height
    reduced_width = 600
    reduced_height = int(reduced_width / aspect_ratio)
    reduced_frame = cv2.resize(frame_arr, (reduced_width, reduced_height))
    bounding_boxes = model.detectMultiScale(reduced_frame, minSize = (30, 30))

    # Draw the bounding boxes over the original frame
    for box in bounding_boxes:
        a, b, width, height = box
        # Recalculate bounding box for the original image
        a = int(a * (original_width / reduced_width))
        b = int(b * (original_height / reduced_height))
        width = int(width * (original_width / reduced_width))
        height = int(height * (original_height / reduced_height))
        cv2.rectangle(frame_arr, (a, b), (a + width, b + height), (255, 0, 255), 2)

    frame['modified'] = frame_arr
