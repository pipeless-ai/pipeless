from .lib.decorators import time

class App():
    """
    Base class for the Retina App
    """

    def __init__(self):
        self.ctx = {}

    @time
    def __before(self, ctx):
        self.before(self, ctx)

    @time
    def __pre_process(self, frame, ctx):
        pass

    @time
    def __process(self, frame, ctx):
        pass

    @time
    def __post_process(self, frame, ctx):
        pass

    @time
    def __after(self, ctx):
        pass

    def start(self):
        self.__before(self.ctx)

        # TODO: while loop for processing


        self.__after(self.ctx)
