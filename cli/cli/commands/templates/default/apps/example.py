from core import app

class Example(app.App):
    """
    Main application class.

    Pre-process, process and post-process hooks, if implemented,
    must return the frame if implemented.

    Note the main class MUST be called like the app
    file to be loaded properly.

    The context can be modified as required to access
    shared vairables between stages.
    """

    # Hook to execute before the processing loop
    def before(self, ctx):
        pass

    # Hook to execute to pre-process each frame
    def pre_process(self, frame, ctx):
        modified_frame = frame # Do something to the frame
        return modified_frame

    # Hook to execute to process each frame
    def process(self, frame, ctx):
        modified_frame = frame # Do something to the frame
        return modified_frame

    # Hook to execute after processing each frame
    def post_process(self, frame, ctx):
        modified_frame = frame # Do something to the frame
        return modified_frame

    # Hook to execute after the processing loop
    def after(self, ctx):
        pass
