import os
import cv2
import numpy as np
from pipeless_ai.lib.app.app import PipelessApp

def box_label(image, box, label='', score=None, color=(255, 0, 255), txt_color=(255, 255, 255)):
    lw = max(round(sum(image.shape) / 2 * 0.003), 2)
    p1, p2 = (int(box[0]), int(box[1])), (int(box[2]), int(box[3]))
    cv2.rectangle(image, p1, p2, color, thickness=lw, lineType=cv2.LINE_AA)
    if label:
        tf = max(lw - 1, 1)  # font thickness
        w, h = cv2.getTextSize(label, 0, fontScale=lw / 3, thickness=tf)[0]  # text width, height
        outside = p1[1] - h >= 3
        p2 = p1[0] + w, p1[1] - h - 3 if outside else p1[1] + h + 3
        cv2.rectangle(image, p1, p2, color, -1, cv2.LINE_AA)  # filled
        if score is not None:
            cv2.putText(image, f'{label} - {score}', (p1[0], p1[1] - 2 if outside else p1[1] + h + 2),
                0, lw / 3, txt_color, thickness=tf, lineType=cv2.LINE_AA)
        else:
            cv2.putText(image, label, (p1[0], p1[1] - 2 if outside else p1[1] + h + 2),
                0, lw / 3, txt_color, thickness=tf, lineType=cv2.LINE_AA)

def overlay_mask(image, mask, color=(255, 0, 255), alpha=0.5, resize=None):
    """
    Combines image and its segmentation mask into a single image.

    Params:
        image: Training image. np.ndarray,
        mask: Segmentation mask. np.ndarray,
        color: Color for segmentation mask rendering.  tuple[int, int, int] = (255, 0, 0)
        alpha: Segmentation mask's transparency. float = 0.5,
        resize: If provided, both image and its mask are resized before blending them together.
        tuple[int, int] = (1024, 1024))

    Returns:
        image_combined: The combined image. np.ndarray
    """
    colored_mask = np.expand_dims(mask, 0).repeat(3, axis=0)
    colored_mask = np.moveaxis(colored_mask, 0, -1)
    masked = np.ma.MaskedArray(image, mask=colored_mask, fill_value=color)
    image_overlay = masked.filled()

    if resize is not None:
        image = cv2.resize(image.transpose(1, 2, 0), resize)
        image_overlay = cv2.resize(image_overlay.transpose(1, 2, 0), resize)

    image_combined = cv2.addWeighted(image, 1 - alpha, image_overlay, alpha, 0)

    return image_combined

class PipelessPlugin(PipelessApp):
    """
    Pipeless plugin to automatically draw results over frames

    You can pass bounding boxes by setting 'self.plugins.draw.boxes' in your Pipeless application.
    It must be an array of boxes in format [x1, y1, x2, y2, label, score, color]
    Color must be a RGB tuple. Ex: (128, 255, 0)

    You can pass segmentation masks by setting 'self.plugins.draw.masks' in your Pipeless application.
    Important: it also expects the same number of bounding boxes when providing masks,
    they will be used to read the score.

    You can pass keypoints by setting 'self.plugins.draw.keypoints' in your Pipeless application.

    To draw results only over a confidence thredshold you can
    set the env var 'PIPELESS_PLUGIN_DRAW_CONFIDENCE_THRESHOLD'

    If a conversion for bounding boxes is required, the following is the standard formula:
    * [x1, y1] = [a, b]
    * [x2, y2] = [a + width, b + height]
    """
    def process(self, frame):
        self.boxes = [] # Reset the bounding box on every frame
        self.masks = [] # Reset the mask on every frame
        self.keypoints = [] # Reset keypoints on every frame
        return frame

    def post_process(self, frame):
        confidence_threshold = float(os.environ.get('PIPELESS_PLUGIN_DRAW_CONFIDENCE_THRESHOLD', None))
        exec_masks_loop = True
        for i, box in enumerate(self.boxes):
            x1, y1, x2, y2, label, score, color = box
            if not confidence_threshold or score > confidence_threshold:
                box_label(frame, [x1, y1, x2, y2], label, score, color)
                if self.masks:
                    exec_masks_loop = False
                    # Draw mask with the same color if provided
                    frame = overlay_mask(frame, self.masks[i], color)

        if exec_masks_loop:
            for mask in self.masks:
                frame = overlay_mask(frame, mask) # Draw without color

        for keypoint in self.keypoints:
            x, y, score = keypoint
            if not confidence_threshold or score > confidence_threshold:
                frame = cv2.circle(frame, (int(x), int(y)), 5, (255, 0, 255), -1)

        return frame