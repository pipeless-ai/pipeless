from pipeless_ai.lib.timer import timer

class PipelessPlugin():
    """
    Base class of a Pipeless plugin

    By implementing methods before and after each hook a plugin can
    receive parameters from the user hook implementation, when
    running after the hook, or pass parameters to the user hook implementation,
    by running before the user hook.
    """

    @timer
    def __before_before(self):
        if hasattr(self, 'before_before') and callable(self.before_before):
            self.before_before()

    @timer
    def __after_before(self):
        if hasattr(self, 'after_before') and callable(self.after_before):
            self.after_before()

    @timer
    def __before_after(self):
        if hasattr(self, 'before_after') and callable(self.before_after):
            self.before_after()

    @timer
    def __after_after(self):
        if hasattr(self, 'after_after') and callable(self.after_after):
            self.after_after()

    @timer
    def __before_pre_process(self, frame):
        if hasattr(self, 'before_pre_process') and callable(self.before_pre_process):
            return self.before_pre_process(frame)
        return frame

    @timer
    def __after_pre_process(self, frame):
        if hasattr(self, 'after_pre_process') and callable(self.after_pre_process):
            return self.after_pre_process(frame)
        return frame

    @timer
    def __before_process(self, frame):
        if hasattr(self, 'before_process') and callable(self.before_process):
            return self.before_process(frame)
        return frame

    @timer
    def __after_process(self, frame):
        if hasattr(self, 'after_process') and callable(self.after_process):
            return self.after_process(frame)
        return frame

    @timer
    def __before_post_process(self, frame):
        if hasattr(self, 'before_post_process') and callable(self.before_post_process):
            return self.before_post_process(frame)
        return frame

    @timer
    def __after_post_process(self, frame):
        if hasattr(self, 'after_post_process') and callable(self.after_post_process):
            return self.after_post_process(frame)
        return frame