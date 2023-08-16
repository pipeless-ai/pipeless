from pipeless_ai.lib.app.app import PipelessApp
from PIL import Image, ImageDraw, ImageFont
import numpy as np

class App(PipelessApp):
    def process(self, frame, ctx):
        pil_image = Image.fromarray(frame)

        text = "Hello pipeless!"
        font = ImageFont.truetype(font='font.ttf', size=60)
        text_color = (255, 0, 255)

        draw = ImageDraw.Draw(pil_image)
        draw.text((800, 600), text, fill=text_color, font=font)

        modified_frame = np.array(pil_image)
        return modified_frame