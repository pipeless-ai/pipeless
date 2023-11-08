import cv2
import numpy as np

def resize_rgb_frame(frame, target_dim):
    target_height = target_dim[0]
    target_width = target_dim[1]
    channels = target_dim[2]
    # Scale the image maintaining aspect ratio
    width_ratio = target_width / frame.shape[1]
    height_ratio = target_height / frame.shape[0]
    # Choose the minimum scaling factor to maintain aspect ratio
    scale_factor = min(width_ratio, height_ratio)
    # Calculate new dimensions after resizing
    new_width = int(frame.shape[1] * scale_factor)
    new_height = int(frame.shape[0] * scale_factor)
    # Calculate padding dimensions
    pad_width = (target_width - new_width) // 2
    pad_height = (target_height - new_height) // 2
    # Create a canvas with the desired dimensions and padding
    canvas = np.zeros((target_height, target_width, channels), dtype=np.uint8)
    # Resize the image and place it on the canvas
    resized_image = cv2.resize(frame, (new_width, new_height))
    canvas[pad_height:pad_height+new_height, pad_width:pad_width+new_width] = resized_image
    return canvas

def hook(frame_data, context):
    frame = frame_data["original"].view()
    yolo_input_shape = (640, 640, 3) # h,w,c
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = resize_rgb_frame(frame, yolo_input_shape)
    frame = cv2.normalize(frame, None, 0.0, 1.0, cv2.NORM_MINMAX)
    frame = np.transpose(frame, axes=(2,0,1)) # Convert to c,h,w
    inference_inputs = frame.astype("float32")
    frame_data['inference_input'] = inference_inputs
