from pipeless_ai.lib.app.app import PipelessApp

class App(PipelessApp):
    def process(self, frame):
        for box in self.plugins.yolov8.bounding_boxes:
            x1, y1, x2, y2, score, class_number = box
            label_string = self.plugins.yolov8.label_from_number(class_number)
            self.plugins.draw.boxes.append([x1, y1, x2, y2, label_string, score, (0, 255, 255)])

        self.plugins.draw.masks = self.plugins.yolov8.masks_data
        self.plugins.draw.keypoints = self.plugins.yolov8.keypoints

        return frame
