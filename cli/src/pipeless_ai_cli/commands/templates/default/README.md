# App project directory

An app is a special class that is loaded by the pipeless framework.

You can see an app as an image processing pipeline. It has some stages (see below) and takes an RGB image to return an RGB image. It could be the same input image, a modified image, or even a totally new image.

In the case of videos, the app code is automatically executed for every frame of the video, so you just need to care about a single image processing and the framework will take care of the rest.

## App stages

An app is build from a set of independent pipeline stages. All stages can be left empty if not required for a particular application.

In some special cases, you may need to maintain some state between two stages. In those cases you can use the app context, represented in the code by the `ctx` variable. You can access the context in all the stages of the pipeline and its value will be preserved between stages when processing a single image and also between pipeline iterations when processing video frames. In short, anything that you add to the context can be accessed and modified at any stage until the app finishes.

### Initial and final stage

These stages are executed only once and do not receive nor return any images. They are used when an app requires to execute some code before processing any image and when it needs to execute some code after processing all the images.

* `before`: code that is executed before starting to process the first frame
* `after`: code that is executed after the processing of the last frame

### Processing stages

These are the stages that actually process the images. They receive the image and they **must** return an image. When not implemented they simply forward the previous stage image to the next stage.

* `pre-process`: code that is executed before the processing of each frame
*  `process`: the actual code that processes a frame
* `post-process`: code that is executed after the processing of each frame
