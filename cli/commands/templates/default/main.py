"""
Main application functions.
You can add custom values to the context in order
to access them from other stages of the processing pipeline
"""

# Hook to execute before the processing loop
def before(ctx):

# Hook to execute to pre-process each frame
def pre_process(ctx, frame):

# Hook to execute to process each frame
def process(ctx, frame):

# Hook to execute after processing each frame
def post_process(ctx, frame):

# Hook to execute after the processing loop
def after(ctx):
