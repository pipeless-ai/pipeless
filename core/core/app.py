from .lib.decorators import timer

class App():
    """
    Base class for the Retina App
    """

    def __init__(self):
        self.ctx = {}

    @timer
    def __before(self, ctx):
        if callable(self.before)
            self.before(ctx)

    @timer
    def __pre_process(self, frame, ctx):
        if callable(self.pre_process):
            self.pre_process(frame, ctx)

    @timer
    def __process(self, frame, ctx):
        if callable(self.process):
            self.process(frame, ctx)

    @timer
    def __post_process(self, frame, ctx):
        if callable(self.post_process):
            self.post_process(frame, ctx)

    @timer
    def __after(self, ctx):
        if callable(self.after):
            self.after(ctx)

    def start(self):
        self.__before(self.ctx)

        # TODO: while loop for processing


        self.__after(self.ctx)
