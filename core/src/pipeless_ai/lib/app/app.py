import types
from pipeless_ai.lib.timer import timer

class PipelessApp():
    """
    Base class to handle an App workflow
    """

    def __init__(self):
        self.plugins = types.SimpleNamespace()
        self.__plugins_exec_graph = ()

    @timer
    def __before(self):
        if hasattr(self, 'before') and callable(self.before):
            self.before()

    @timer
    def __pre_process(self, frame):
        if hasattr(self, 'pre_process') and callable(self.pre_process):
            return self.pre_process(frame)
        return frame

    @timer
    def __process(self, frame):
        if hasattr(self, 'process') and callable(self.process):
            return self.process(frame)
        return frame

    @timer
    def __post_process(self, frame):
        if hasattr(self, 'post_process') and callable(self.post_process):
            return self.post_process(frame)
        return frame

    @timer
    def __after(self):
        if hasattr(self, 'after') and callable(self.after):
            self.after()
