from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os

def hook(frame, context):
     pil_image = Image.fromarray(frame['modified'])
     text = "Hello pipeless!"
     font = ImageFont.truetype(font='/home/path/pipeless/examples/wattermark/font.ttf', size=60)
     text_color = (255, 0, 255)

     draw = ImageDraw.Draw(pil_image)
     draw.text((800, 600), text, fill=text_color, font=font)

     modified_frame = np.array(pil_image)
     frame['modified'] = modified_frame
     print(context)
