import simpleaudio as sa
import numpy as np
import math
import cv2

# In post-process we will simply play the piano
def hook(frame_data, _):
    results = frame_data['inference_output']
    print(results)
    if len(results) <= 0:
        return

    p1 = results[0]
    p2 = results[1]

    center = [int(x) for x in p1] # center of the eye

    w = p2[0] - p1[0]
    h = p2[1] - p1[1]
    angle = math.atan2(h, w)
    if angle < 0:
        angle += 2*math.pi

    if is_point_outside_circle(p2, center, 20):
        note_duration = 1 / frame_data['fps'] # make each note last the duration of one frame
        notes = [261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88, 523.25]
        if angle > 15*math.pi/8 and angle < math.pi/8:
            play_sound(notes[6], note_duration)
        elif angle > math.pi/8 and angle < 3*math.pi/8:
            play_sound(notes[5], note_duration)
        elif angle > 3*math.pi/8 and angle < 5*math.pi/8:
            play_sound(notes[4], note_duration)
        elif angle > 5*math.pi/8 and angle < 7*math.pi/8:
            play_sound(notes[3], note_duration)
        elif angle > 7*math.pi/8 and angle < 9*math.pi/8:
            play_sound(notes[2], note_duration)
        elif angle > 9*math.pi/8 and angle < 11*math.pi/8:
            play_sound(notes[1], note_duration)
        elif angle > 11*math.pi/8 and angle < 13*math.pi/8:
            play_sound(notes[0], note_duration)
        elif angle > 13*math.pi/8 and angle < 15*math.pi/8:
            play_sound(notes[7], note_duration)

    # Show with mirror effect
    flipped = cv2.flip(frame_data['modified'], 1)
    flipped_eye_center = (frame_data['width'] - center[0] - 1, center[1])
    draw_piano(flipped, flipped_eye_center)
    frame_data['modified'] = flipped

def play_sound(note, duration):
    sample_rate = 44100  # Hz
    samples = (32767 * 0.5 * np.sin(2.0 * np.pi * np.arange(sample_rate * duration) * note / sample_rate)).astype(np.int16)
    wave_obj = sa.WaveObject(samples, 1, 2, sample_rate)
    play_obj = wave_obj.play()
    play_obj.wait_done()

def draw_piano(frame, center):
    num_radii = 8
    init_angle = np.pi / 8
    angle_step = np.pi / 4 # 2 * pi / 8 (45 degrees)

    radius = 2 * (min(center[0], center[1]) - 10)

    labels = ["Mi", "Fa", "Sol", "La", "Si", "do", "Do", "Re"]
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    font_thickness = 1
    font_color = (0, 0, 255)

    for i in range(num_radii):
        angle = init_angle + i * angle_step
        x_end = int(center[0] + radius * np.cos(angle))
        y_end = int(center[1] + radius * np.sin(angle))
        cv2.line(frame, center, (x_end, y_end), (0, 0, 255), 2)

        cv2.circle(frame, center, 20, (255, 0, 0), 2)

        text_angle = angle - np.pi / 8
        text_x_end = int(center[0] + radius / 2 * np.cos(text_angle))
        text_y_end = int(center[1] + radius / 2 * np.sin(text_angle))
        cv2.putText(frame, labels[i], (text_x_end, text_y_end), font, font_scale, font_color, font_thickness, cv2.LINE_AA)


def is_point_outside_circle(point, center, radius):
    distance = math.sqrt((point[0] - center[0])**2 + (point[1] - center[1])**2)
    return distance > radius
