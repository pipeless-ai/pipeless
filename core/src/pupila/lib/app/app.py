from pupila.lib.timer import timer

class PupilaApp():
    """
    Base class to handle an App workflow
    """

    def __init__(self):
        self.ctx = {}

    @timer
    def __before(self):
        if hasattr(self, 'before') and callable(self.before):
            self.before(self.ctx)

    @timer
    def __pre_process(self, frame):
        if hasattr(self, 'pre_process') and callable(self.pre_process):
            return self.pre_process(frame, self.ctx)
        return frame

    @timer
    def __process(self, frame):
        if hasattr(self, 'process') and callable(self.process):
            return self.process(frame, self.ctx)
        return frame

    @timer
    def __post_process(self, frame):
        if hasattr(self, 'post_process') and callable(self.post_process):
            return self.post_process(frame, self.ctx)
        return frame

    @timer
    def __after(self):
        if hasattr(self, 'after') and callable(self.after):
            self.after(self.ctx)
