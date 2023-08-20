import tensorflow as tf
import math

from pipeless_ai_tf_models.tflite import TfLiteModel

model_url = 'https://tfhub.dev/google/lite-model/movenet/multipose/lightning/tflite/float16/1?lite-format=tflite'

class MultiPoseEstimationLightning(TfLiteModel):

    def __init__(self):
        super.__init__(model_url)

    def prepare_input(self, rgb_frame):
        image = tf.expand_dims(image, axis=0)
        resized_image, image_shape = resize_with_aspect_ratio(image, 256)
        #image_tensor = tf.cast(resized_image, dtype=tf.uint8)
        input_tensor = tf.cast(resized_image, dtype=tf.uint8)
        return input_tensor

    def infer(self, input_tensor):
        input_details = self.interpreter.get_input_details()
        output_details = self.interpreter.get_output_details()

        is_dynamic_shape_model = input_details[0]['shape_signature'][2] == -1
        if is_dynamic_shape_model:
            input_tensor_index = input_details[0]['index']
            input_shape = input_tensor.shape
            self.interpreter.resize_tensor_input(
                input_tensor_index, input_shape, strict=True)

        self.interpreter.allocate_tensors()
        self.interpreter.set_tensor(input_details[0]['index'], input_tensor.numpy())
        self.interpreter.invoke()
        keypoints_with_scores = self.interpreter.get_tensor(output_details[0]['index'])

        return keypoints_with_scores

    def process_output(self, output):
        return output # Nothing to do in this model

def resize_with_aspect_ratio(image, target_size):
    _, height, width, _ = image.shape
    if height > width:
        scale = float(target_size / height)
        target_height = target_size
        scaled_width = math.ceil(width * scale)
        image = tf.image.resize(image, [target_height, scaled_width])
        target_width = int(math.ceil(scaled_width / 32) * 32)
    else:
        scale = float(target_size / width)
        target_width = target_size
        scaled_height = math.ceil(height * scale)
        image = tf.image.resize(image, [scaled_height, target_width])
        target_height = int(math.ceil(scaled_height / 32) * 32)
    image = tf.image.pad_to_bounding_box(image, 0, 0, target_height, target_width)
    return (image,  (target_height, target_width))
