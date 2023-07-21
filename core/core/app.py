from lib.decorators import time

class App():
    """
    Base class for the Retina App
    """

    def __init__(self):
        self.ctx = {}

    @time
    def before(self, ctx):
        pass

    @time
    def pre_process(self, frame, ctx):
        pass

    @time
    def process(self, frame, ctx):
        pass

    @time
    def post_process(self, frame, ctx):
        pass

    @time
    def after(self, ctx):
        pass

    def start(self):
        self.before(self.ctx)

        # TODO: while loop for processing
        self.pre_process(self.)

        self.after(self.ctx)
