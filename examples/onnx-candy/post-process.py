import numpy as np
import cv2

def hook(frame_data, _):
    inference_results = frame_data["inference_output"]
    candy_image = inference_results[0] # Remove batch axis
    candy_image = np.clip(candy_image, 0, 255)
    candy_image = candy_image.transpose(1,2,0).astype("uint8")

    # Pad the result image to the original shape
    desired_height, desired_width, _ = frame_data['original'].shape
    current_height, current_width, _ = candy_image.shape
    pad_width = max(0, desired_width - current_width)
    pad_height = max(0, desired_height - current_height)
    top = pad_height // 2
    bottom = pad_height - top
    left = pad_width // 2
    right = pad_width - left
    padding_color = [255, 255, 255]
    padded_image = cv2.copyMakeBorder(candy_image, top, bottom, left, right, cv2.BORDER_CONSTANT, value=padding_color)

    frame_data["modified"] = padded_image
