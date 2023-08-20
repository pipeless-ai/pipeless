import tensorflow as tf
import math
import numpy as np
import pkg_resources

from pipeless_ai_tf_models.tflite import TfLiteModel

model_path = pkg_resources.resource_filename('pipeless_ai_tf_models.multi_pose_estimation', 'MultiPoseEstimationLightning.tflite')

class MultiPoseEstimationLightning(TfLiteModel):
    """
    Model Ref: https://tfhub.dev/google/lite-model/movenet/multipose/lightning/tflite/float16/1?lite-format=tflite
    """
    def __init__(self):
        super().__init__(model_path=model_path)

    def prepare_input(self, rgb_frame):
        self.original_image_shape = rgb_frame.shape
        image = tf.expand_dims(rgb_frame, axis=0)
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
        """
        Process output to return bounding boxes and keypoints.
        See the output format on the model documentation
        Ref: https://tfhub.dev/google/lite-model/movenet/multipose/lightning/tflite/float16/1

        Returns
        -   bboxes in format [ymin, xmin, ymax, xmax]
        -   keypoints in format [x, y]
        """
        keypoints_and_boxes = output[0, :, :]
        keypoints = keypoints_and_boxes[:, :51]  # Extract keypoints [y, x, s]
        boxes = keypoints_and_boxes[:, 51:]      # Extract boxes [ymin, xmin, ymax, xmax, score]

        output_bboxes = []
        output_keypoints = []

        # Loop through each instance
        for i in range(len(keypoints)):
            instance_keypoints = keypoints[i, :]
            instance_box = boxes[i, :]

            # Reshape keypoints to match [y, x, s] format
            instance_keypoints = instance_keypoints.reshape((-1, 3))

            # Convert normalized coordinates to pixel values
            img_height, img_width, _ = self.original_image_shape
            instance_keypoints[:, :2] = instance_keypoints[:, :2] * np.array([img_height, img_width])

            # Get bounding box
            ymin, xmin, ymax, xmax, b_score = instance_box
            bbox = (
                int(ymin * img_height), int(xmin * img_width),
                int(ymax * img_height), int(xmax * img_width)
            )
            if b_score > 0.5:
               output_bboxes.append(bbox)

            # Get keypoints
            for j in range(0, 17):
                keypoint_y, keypoint_x, keypoint_score = instance_keypoints[j]
                if keypoint_score > 0.5:
                    output_keypoints.append((int(keypoint_x), int(keypoint_y)))

        return output_bboxes, output_keypoints

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
