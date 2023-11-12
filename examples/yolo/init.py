from ultralytics import YOLO

def init():
    return { "model": YOLO('yolov8n.pt') }