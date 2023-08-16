from pipeless.lib.app.app import PipelessApp

class App(PipelessApp):
    """
    Main application class.

    Pre-process, process and post-process hooks, if implemented,
    must return a RGB image.

    The context can be accessed and modified at any stage of the pipeline.
    You can use it to share data between stages or pipeline iterations (i.e
    between the processing of different frames)
    """

    # Hook to execute before the processing of the first image
    def before(self, ctx):
        pass

    # Hook to execute to pre-process each image
    def pre_process(self, frame, ctx):
        modified_frame = frame # Do something to the frame
        return modified_frame

    # Hook to execute to process each image
    def process(self, frame, ctx):
        modified_frame = frame # Do something to the frame
        return modified_frame

    # Hook to execute after processing each image
    def post_process(self, frame, ctx):
        modified_frame = frame # Do something to the frame
        return modified_frame

    # Hook to execute after the processing of the last image
    def after(self, ctx):
        pass
