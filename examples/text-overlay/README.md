# Hello Pipeless!

Let's do the most basic stuff we can do with pipeless.

In this example we will write some text directly into a video and show the video directly on the screen while it is processed.

## Requirements

* NumPy: `pip install numpy`
* Pillow: `pip install Pillow`

> NOTE: this directory includes a video you can use for testing as well as font file, so you just need to install the python dependencies.

## Run the example

1. Clone the repo and install the pipeless framework

1. Update `config.yaml` with the path you used to clone the repo (update the input video path). It **must** be an absolute path.

1. Move into the `overlay-text` directory

1. Execute from the `overlay-text` directory:

```console
pipeless run
```

## Walkthrough

In this example we only implement the `processing` stage.

First , we create a pillow image from the frame array and define the text that will be drawn and the text font and color

```python
pil_image = Image.fromarray(frame)
text = "Hello pipeless!"
font = ImageFont.truetype(font='font.ttf', size=60)
text_color = (255, 0, 255)
```

Then, we simply draw the text image over our frame:

```python
    draw = ImageDraw.Draw(pil_image)
    draw.text((800, 600), text, fill=text_color, font=font)
```

And finally, we return the modified frame as a NumPy array:

```python
    modified_frame = np.array(pil_image)
    return modified_frame
```