import numpy as np
import time

def hook(frame, context):
    rgb_frame = frame['original']
    model = context['model']
    input_fps = frame['fps']
    delay = time.time() - frame['input_ts']
    if delay > 1 / input_fps:
       print('Skipping frame to maintain real-time')
    else:
        prediction = next(model(rgb_frame, stream=True))
        bboxes = prediction.boxes.data.tolist() if prediction.boxes else []
        frame['inference_output'] = np.array(bboxes, dtype="float32")
