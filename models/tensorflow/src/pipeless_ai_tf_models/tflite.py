import requests
import tensorflow as tf

from pipeless_ai.models.tflite import TfLiteModelInterface

class TfLiteModel(TfLiteModelInterface):
    """
    Base class with common implementation of TFLite models
    """
    def __init__(self, model_url):
        url_response = requests.get(model_url)
        model_file_path = f'{self.__class__.__name__}.tflite'
        with open(model_file_path, "wb") as model_file:
            model_file.write(url_response.content)

        self.interpreter= tf.lite.Interpreter(model_file_path)

    def update_signature(self, signature_name=None):
        """
        Update the loaded signature from the model
        """
        if signature_name is not None:
            self.signature = self.interpreter.get_signature_runner(signature_name)
        else:
            self.signature = self.interpreter.get_signature_runner()

    def prepare_input(self, **kwargs):
        """
        To be implemented by the specific model
        Must return the processed input data
        """
        pass

    def infer(self, input_tensor):
        """
        Invoke inference on the loaded signature providing the params.
        This implements a common inference, but can be overriden by specific models
        Ex:
            model.infer(x=tf.constant([1.0], shape=(1,10), dtype=tf.float32))
        """
        return self.signature(input_tensor)

    def process_output(self, output):
        """
        To be implemented by the specific model
        Must return the processed output data in a format usefull for the application
        """
        pass

    def invoke_inference(self, rgb_frame):
        frame_input_tensor = self.prepare_input(rgb_frame)
        raw_output = self.infer(frame_input_tensor)
        output = self.process_output(raw_output)
        return output