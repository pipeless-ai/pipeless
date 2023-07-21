from .lib.decorators import timer

class App():
    """
    Base class for the Retina App
    """

    def __init__(self):
        self.ctx = {}

    @timer
    def __before(self, ctx):
        self.before(ctx)

    @timer
    def __pre_process(self, frame, ctx):
        pass

    @timer
    def __process(self, frame, ctx):
        pass

    @timer
    def __post_process(self, frame, ctx):
        pass

    @timer
    def __after(self, ctx):
        pass

    def start(self):
        self.__before(self.ctx)

        # TODO: while loop for processing


        self.__after(self.ctx)
