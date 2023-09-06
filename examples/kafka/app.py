from pipeless_ai.lib.app.app import PipelessApp
from pipeless_ai_plugins.kafka import KafkaProducer
import cv2

class App(PipelessApp):
    def before(self):
        self.producer = KafkaProducer()
        self.xml_data = cv2.CascadeClassifier('cats.xml')

    def process(self, frame):
        model = self.xml_data

        # Create reduced frame for faster detection
        original_height, original_width, _ = frame.shape
        aspect_ratio = original_width / original_height
        reduced_width = 600
        reduced_height = int(reduced_width / aspect_ratio)
        reduced_frame = cv2.resize(frame, (reduced_width, reduced_height))
        bounding_boxes = model.detectMultiScale(reduced_frame, minSize = (30, 30))

        # Notify that there is a cat
        if len(bounding_boxes) > 0:
            self.producer.produce('pipeless', 'There is a cat!')
