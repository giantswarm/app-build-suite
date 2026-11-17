from step_exec_lib.errors import Error


class GiantSwarmValidatorError(Error):
    pass


class IconUnavailableError(GiantSwarmValidatorError):
    """The icon can't be fetched right now: its host is down or the icon isn't published yet."""
