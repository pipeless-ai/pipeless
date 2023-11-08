import cv2

def init():
    return {
        'model': cv2.CascadeClassifier('/home/miguelaeh/projects/pipeless-rust/examples/cats/cats.xml')
    }