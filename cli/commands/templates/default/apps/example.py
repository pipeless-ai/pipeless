"""
Main application class.

Note the main class MUST be called like the app
file to be loaded properly.

The context can be modified as required to access
shared vairables between stages.
"""

import retina

class Example(retina.App):

    # Hook to execute before the processing loop
    def before(self, ctx):
        pass

    # Hook to execute to pre-process each frame
    def pre_process(self, frame, ctx):
        pass

    # Hook to execute to process each frame
    def process(self, frame, ctx):
        pass

    # Hook to execute after processing each frame
    def post_process(self, frame, ctx):
        pass

    # Hook to execute after the processing loop
    def after(self, ctx):
        pass
