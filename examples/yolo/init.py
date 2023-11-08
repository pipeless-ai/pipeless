from ultralytics import YOLO
from ultralytics.utils.ops import scale_image

def init():
    return { "model": YOLO('yolov8n.pt') }