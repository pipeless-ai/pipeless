from pupila.lib.timer import timer

class App():
    """
    Base class to handle an App workflow
    """

    def __init__(self):
        self.ctx = {}

    @timer
    def __before(self):
        if callable(self.before):
            self.before(self.ctx)

    @timer
    def __pre_process(self, frame):
        if callable(self.pre_process):
            return self.pre_process(frame, self.ctx)
        return frame

    @timer
    def __process(self, frame):
        if callable(self.process):
            return self.process(frame, self.ctx)
        return frame

    @timer
    def __post_process(self, frame):
        if callable(self.post_process):
            return self.post_process(frame, self.ctx)
        return frame

    @timer
    def __after(self):
        if callable(self.after):
            self.after(self.ctx)

    # To be implemented by the user
    @abstractmethod
    def before(ctx):
        pass
    @abstractmethod
    def pre_process(frame, ctx):
        pass
    @abstractmethod
    def process(frame, ctx):
        pass
    @abstractmethod
    def post_process(frame, ctx):
        pass
    @abstractmethod
    def after(ctx):
        pass
