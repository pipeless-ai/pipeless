import sys
import cv2
import numpy as np
import requests

from pipeless_ai.lib.logger import logger

def get_inference_session(config):
    """
    Returns an inference session when possible or None
    """
    if config.get_worker().get_inference().get_model_uri():
        try:
            # Do not import by default since we have different flavors for CPU and GPU
            from pipeless_ai.lib.worker.inference.runtime import PipelessInferenceSession
            inference_config = config.get_worker().get_inference()
            return PipelessInferenceSession(inference_config)
        except ImportError or ModuleNotFoundError as e:
            logger.error('''Unable to import the ONNX Runtime.
Did you install the ONNX Pipeless flavor?
To install the ONNX Pipeless flavor for CPU use:
    "pip install pipeless-ai\[onnx-cpu]"
To install the ONNX Pipeless flavor for GPU use:
    "pip install pipeless-ai\[onnx-gpu]"
''')
            raise e

    return None

def get_model_path(uri: str, alias: str) -> str:
    """
    Obtains the model from the provided URI.
    Returns the local path.
    """
    # TODO: support download from private s3 buckets
    if uri.startswith('file'):
        model_file_path = uri.replace("file://", "")
    elif uri.startswith('http'):
        url_response = requests.get(uri)
        model_file_path = f'/tmp/{alias}-model.onnx'
        with open(model_file_path, "wb") as model_file:
            model_file.write(url_response.content)
    else:
        raise ValueError("The model URI currently supports 'file://' and 'http(s)://'")

    return model_file_path

def get_transpose_indexes(format):
    """
    Calculate the indexes required to transpose an image to match the model input format
    Takes a format like: "width, height, channels"
    """
    dimension_mapping = {"height": 0, "width": 1, "channels": 2}
    # Create a list of permutation indices based on the transpose order
    permute_indexes = [dimension_mapping[dim] for dim in format]
    return permute_indexes

def transpose_image(image, format):
    """
    Receives an image and the expected format like: "width, height, channels"
    Returns the image in the expected format
    """
    permute_indexes = get_transpose_indexes(format)
    transposed_image = np.transpose(image, permute_indexes)
    return transposed_image

def parse_input_shape(input_shape, format, force_tuple):
    """
    Parse the image format from the model input using the format provided
    Returns batch_size, channels, height, width of the ONNX model input
    We assume the batch size is always the outer dimmension
    """
    new_order = ("channels", "height", "width")
    if len(input_shape) == 3:
        batch_size = None
        sub_shape = input_shape
    elif len(input_shape) == 4:
        batch_size = input_shape[0] # Assume the batch size is the first dimmension
        sub_shape = input_shape[-3:]
    else:
        raise ValueError(f'Unsupported model input shape: {input_shape}')

    force_width, force_height, force_channels = force_tuple
    key_to_value = dict(zip(format, sub_shape))
    if force_width:
        key_to_value['width'] = int(force_width)
    if force_height:
        key_to_value['height'] = int(force_height)
    if force_channels:
        key_to_value['channels'] = int(force_channels)
    new_sub_shape = tuple(key_to_value[key] for key in new_order)
    return batch_size, *new_sub_shape

def prepare_frames(frames, input_dtype, input_shape_format, batch_size, target_height=None, target_width=None):
    out_frames = []
    for frame in frames:
        if target_height and target_width:
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
            canvas = np.zeros((target_height, target_width, frame.shape[2]), dtype=np.uint8)
            # Resize the image and place it on the canvas
            resized_image = cv2.resize(frame, (new_width, new_height))
            canvas[pad_height:pad_height+new_height, pad_width:pad_width+new_width] = resized_image
            frame = canvas
        elif (target_width and not target_height) or (target_height and not target_width):
            logger.error("Can't resize to a single dimmension. Please provide both tagert_width and target_height")
            sys.exit(1)

        if input_dtype == 'tensor(float)':
            frame = frame.astype(np.float32)

        if input_shape_format:
            frame = transpose_image(frame, input_shape_format) # [h,w,channels] to the specified shape

        out_frames.append(frame)
    return np.array(out_frames)