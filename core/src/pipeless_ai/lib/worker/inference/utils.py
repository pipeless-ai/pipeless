import sys
import cv2
import numpy as np
import onnx
import requests

from pipeless_ai.lib.logger import logger

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

def load_model(file: str, alias: str, force_opset_version: int | None =None, force_ir_version: int | None = None):
    """
    Loads a model with onnx and checks it.
    Returns the model if correct. Finishes execution otherwise.
    """
    # TODO: convert the model on the fly checking the extensions from the most common frameworks. Or implement conversion in the CLI instead.
    try:
        logger.info(f'Checking {alias} inference model')
        model = onnx.load(file)
        if force_opset_version:
            logger.info(f'Converting from OpSet version {model.opset_import[0].version} to {force_opset_version}')
            model = onnx.version_converter.convert_version(model, force_opset_version)
        if force_ir_version:
            logger.info(f'Converting from IR version {model.ir_version} to {force_opset_version}')
            model.ir_version = force_ir_version
        onnx.checker.check_model(model)
        logger.info(f'Model operation set (OpSet) version: {model.opset_import[0].version}')
        logger.info(f'Model intermediate representation (IR) version: {model.ir_version}')
    except Exception as e:
        logger.error(f'Error loading the {alias} model: {e}')
        sys.exit(1)

    return model

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

def prepare_frame(frame, input_dtype, input_shape_format, batch_size, target_height=None, target_width=None):
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

    if batch_size:
        # Since this is a single frame just expand the dims
        frame = np.expand_dims(frame, axis=0)

    return frame