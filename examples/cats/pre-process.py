import cv2

def hook(frame_data, _):
    rgb_frame_arr = frame_data['original']

    # Create reduced frame for faster detection
    original_height, original_width, _ = rgb_frame_arr.shape
    aspect_ratio = original_width / original_height
    reduced_width = 600
    reduced_height = int(reduced_width / aspect_ratio)
    reduced_frame = cv2.resize(rgb_frame_arr, (reduced_width, reduced_height))

    frame_data['modified'] = reduced_frame
