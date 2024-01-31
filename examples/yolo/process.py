import numpy as np

def hook(frame, context):
    rgb_frame = frame['original']
    model = context['model']
    prediction = next(model(rgb_frame, stream=True))
    bboxes = prediction.boxes.data.tolist() if prediction.boxes else []
    frame['inference_output'] = np.array(bboxes, dtype="float32")
