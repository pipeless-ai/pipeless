class App():
    """
    Base class for the Retina App
    """

    def __init__(self):
        self.ctx = {}

    def before(self, ctx):
        pass

    def pre_process(self, frame, ctx):
        pass

    def process(self, frame, ctx):
        pass

    def post_process(self, frame, ctx):
        pass

    def after(self, ctx):
        pass

    def start(self):
        self.before(self.ctx)

        # TODO: while loop for processing
        self.pre_process(self.)

        self.after(self.ctx)
