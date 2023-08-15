# Cats Face Recognition with Pipeless

This example app uses Pipeless to recognize cats faces on a video stream.

## Requirements

* Pipeless framework

* OpenCV. Install it by running:

```console
pip install opencv-python
```

## Run the example

1. Clone the repo and install the pipeless framework

1. Update `config.yaml` with the paths used within your system. They **must be absolute paths**.

1. Move into the `cats` directory

1. Execute:

```console
pipeless run
```

You can now use any video player to see the results. For example:

```console
mpv cats-output.mp4
```

## Walkthrough

### Before stage

In order to recognise cats we need to load a model trained for that purpose.
Since we want to load the model before any frame is processed, we do it within the `before` stage (method).

```python
xml_data = cv2.CascadeClassifier('cats.xml')
```

After loading the model, we store it on the app context (`ctx`) in order to have access during other stage iterations.

```python
ctx['xml_data'] = xml_data
```

### Process stage

We will do basic processing here in order to recognise cat faces on the frames and draw a square around them.

First, we get a reference to the model that we added to the context on the `before` stage:

```python
model = ctx['xml_data']
```

Detecting cats is faster on smaller images so we resize the original frame:

```python
original_height, original_width, _ = frame.shape
aspect_ratio = original_width / original_height
reduced_width = 600
reduced_height = int(reduced_width / aspect_ratio)
reduced_frame = cv2.resize(frame, (reduced_width, reduced_height))
```

Then, we just obtain the cats on the frame by passing the frame through the model:

```python
bounding_boxes = model.detectMultiScale(reduced_frame, minSize = (30, 30))
```

Finally, we draw the bounding boxes over the original frame. To do that, we need to scale the bounding boxes since they were calcuated for the reduced frame:

```python
for box in bounding_boxes:
    a, b, width, height = box
    # Recalculate bounding box for the original image
    a = int(a * (original_width / reduced_width))
    b = int(b * (original_height / reduced_height))
    width = int(width * (original_width / reduced_width))
    height = int(height * (original_height / reduced_height))
    # Draw the bounding box
    cv2.rectangle(frame, (a, b), (a + width, b + height), (255, 0, 255), 2)
```

And that's all. The framework will do the rest for us.