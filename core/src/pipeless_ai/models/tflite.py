from abc import ABC, abstractmethod

class TfLiteModelInterface(ABC):
    """
    Interface to use Tensorflow Lite based models
    """

    @abstractmethod
    def __init__(self, model_url):
        pass

    @abstractmethod
    def update_signature(self, signature_name=None):
        """
        Update the loaded signature from the model
        """
        pass

    @abstractmethod
    def prepare_input(self, **kwargs):
        """
        To be implemented by the specific model
        Must return the processed input data
        """
        pass

    @abstractmethod
    def infer(self, **kwargs):
        """
        Invoke inference on the loaded signature providing the params
        Ex:
            model.infer(x=tf.constant([1.0], shape=(1,10), dtype=tf.float32))
        """
        pass

    @abstractmethod
    def process_output(self, output):
        """
        To be implemented by the specific model
        Must return the processed output data in a format usefull for the application
        """
        pass