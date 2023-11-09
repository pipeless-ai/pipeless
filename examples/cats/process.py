import numpy as np

def hook(frame_data, context):
    model = context['model']
    reduced_frame = frame_data['modified']
    bounding_boxes = model.detectMultiScale(reduced_frame, minSize = (30, 30))

    frame_data['inference_output'] = np.array(bounding_boxes).astype("float32")
