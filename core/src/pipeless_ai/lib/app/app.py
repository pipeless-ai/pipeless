import types
from line_profiler import LineProfiler

class PipelessApp():
    """
    Base class to handle an App workflow
    """

    def __init__(self):
        self.original_frame = None
        self.inference = types.SimpleNamespace()
        self.plugins = types.SimpleNamespace()
        self.__plugins_exec_graph = ()
        self.__profiler = None # To be enabled based on the user config

    def __before(self):
        if hasattr(self, 'before') and callable(self.before):
            self.before()

    def __pre_process(self, frame):
        if hasattr(self, 'pre_process') and callable(self.pre_process):
            return self.pre_process(frame)
        return frame

    def __process(self, frame):
        if hasattr(self, 'process') and callable(self.process):
            return self.process(frame)
        return frame

    def __post_process(self, frame):
        if hasattr(self, 'post_process') and callable(self.post_process):
            return self.post_process(frame)
        return frame

    def __after(self):
        if hasattr(self, 'after') and callable(self.after):
            self.after()

    def __enable_profiler(self):
        self.__profiler = LineProfiler()
        self.__profiler.enable_by_count()
        for hook in ['before', 'pre_process', 'process', 'post_process', 'after']:
            if hasattr(self, hook) and callable(getattr(self, hook)):
                self.__profiler.add_function(getattr(self, hook))

    def __print_profiler_stats(self):
        if self.__profiler is not None:
            self.__profiler.print_stats()
