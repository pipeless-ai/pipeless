from pipeless_ai.lib.app.app import PipelessApp

class App(PipelessApp):
    # Hook to execute before the processing of the first image
    def before(self):
        pass

    # Hook to execute to pre-process each image
    def pre_process(self, frame):
        modified_frame = frame # Do something to the frame
        return modified_frame

    # Hook to execute to process each image
    def process(self, frame):
        modified_frame = frame # Do something to the frame
        return modified_frame

    # Hook to execute after processing each image
    def post_process(self, frame):
        modified_frame = frame # Do something to the frame
        return modified_frame

    # Hook to execute after the processing of the last image
    def after(self):
        pass
