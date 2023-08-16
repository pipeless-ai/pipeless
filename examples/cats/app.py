from pipeless.lib.app.app import PipelessApp
from pipeless.lib.logger import logger
import cv2

class App(PipelessApp):
    def before(self, ctx):
        # Load the model before processing any frame
        xml_data = cv2.CascadeClassifier('cats.xml')
        ctx['xml_data'] = xml_data

    def process(self, frame, ctx):
        model = ctx['xml_data']

        # Create reduced frame for faster detection
        original_height, original_width, _ = frame.shape
        aspect_ratio = original_width / original_height
        reduced_width = 600
        reduced_height = int(reduced_width / aspect_ratio)
        reduced_frame = cv2.resize(frame, (reduced_width, reduced_height))
        bounding_boxes = model.detectMultiScale(reduced_frame, minSize = (30, 30))

        # Draw the bounding boxes over the original frame
        for box in bounding_boxes:
            a, b, width, height = box
            # Recalculate bounding box for the original image
            a = int(a * (original_width / reduced_width))
            b = int(b * (original_height / reduced_height))
            width = int(width * (original_width / reduced_width))
            height = int(height * (original_height / reduced_height))
            cv2.rectangle(frame, (a, b), (a + width, b + height), (255, 0, 255), 2)

        return frame
