import cv2

def hook(frame_data, context):
    frame = frame_data["modified"]
    height, width, channels = frame.shape
    scale = 450 / max(height, width)
    resized_frame = cv2.resize(frame, (round(scale * width), round(scale * height)))
    # The input for the Roboflow inference server is the image
    frame_data["inference_input"] = resized_frame.astype('float32')
