import cv2
import numpy as np

def is_cuda_available():
    return cv2.cuda.getCudaEnabledDeviceCount() > 0

"""
Resize and pad image. Uses CUDA when available
"""
def resize_and_pad(frame, target_dim, pad_top, pad_bottom, pad_left, pad_right):
    target_height, target_width = target_dim
    if is_cuda_available():
        # FIXME: due to the memory allocation here could be even slower than running on CPU. We must provide the frame from GPU memory to the hook
        frame_gpu = cv2.cuda_GpuMat(frame)
        resized_frame_gpu = cv2.cuda.resize(frame_gpu, (target_width, target_height), interpolation=cv2.INTER_CUBIC)
        padded_frame_gpu = cv2.cuda.copyMakeBorder(resized_frame_gpu, pad_top, pad_bottom, pad_left, pad_right, cv2.BORDER_CONSTANT, value=(0, 0, 0))
        result = padded_frame_gpu.download()
        return result
    else:
        resized_frame = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_CUBIC)
        padded_frame = cv2.copyMakeBorder(resized_frame, pad_top, pad_bottom, pad_left, pad_right,
                        borderType=cv2.BORDER_CONSTANT, value=(0, 0, 0))
        return padded_frame

def resize_with_padding(frame, target_dim):
    target_height, target_width, _ = target_dim
    frame_height, frame_width, _ = frame.shape

    width_ratio = target_width / frame_width
    height_ratio = target_height / frame_height
    # Choose the minimum scaling factor to maintain aspect ratio
    scale_factor = min(width_ratio, height_ratio)
    # Calculate new dimensions after resizing
    new_width = int(frame_width * scale_factor)
    new_height = int(frame_height * scale_factor)
    # Calculate padding dimensions
    pad_width = (target_width - new_width) // 2
    pad_height = (target_height - new_height) // 2

    padded_image = resize_and_pad(frame, (new_height, new_width), pad_height, pad_height, pad_width, pad_width)
    return padded_image

def hook(frame_data, _):
    frame = frame_data["original"].view()
    yolo_input_shape = (640, 640, 3) # h,w,c
    frame = resize_with_padding(frame, yolo_input_shape)
    frame = np.array(frame) / 255.0 # Normalize pixel values
    frame = np.transpose(frame, axes=(2,0,1)) # Convert to c,h,w
    inference_inputs = frame.astype("float32")
    frame_data['inference_input'] = inference_inputs
