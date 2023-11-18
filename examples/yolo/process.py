import numpy as np
import time

def hook(frame, context):
    start = time.time()
    rgb_frame = frame['original']
    model = context['model']
    input_fps = frame['fps']
    raw_samples = pipeless_kvs_get('samples')
    samples = int(raw_samples) if raw_samples else 0
    raw_avg_time = pipeless_kvs_get('avg_process_time')
    avg_time = float(raw_avg_time) if raw_avg_time else 0

    if should_skip_frame(avg_time, input_fps):
        print('Skipping frame to maintain real-time')
    else:
        prediction = next(model(rgb_frame, stream=True))
        bboxes = prediction.boxes.data.tolist() if prediction.boxes else []
        frame['inference_output'] = np.array(bboxes, dtype="float32")

    exec_time = time.time() - start
    new_avg_time = (avg_time * samples + exec_time) / (samples + 1)
    pipeless_kvs_set('samples', samples + 1)
    pipeless_kvs_set('avg_process_time', new_avg_time)

def should_skip_frame(avg_execution_time, desired_fps):
    max_process_time = 1 / desired_fps
    return avg_execution_time > max_process_time
