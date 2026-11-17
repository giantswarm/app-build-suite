from step_exec_lib.errors import Error


class GiantSwarmValidatorError(Error):
    pass


class IconUnavailableError(GiantSwarmValidatorError):
    """The icon can't be fetched right now: its host is down or the icon isn't published yet."""


class IconNotPublishedError(IconUnavailableError):
    """The icon host answered with HTTP 404, usually because the icon isn't published yet."""


# Deprecated: the name released in v2.5.3 and v2.6.0, kept for existing importers.
IconHostUnreachableError = IconUnavailableError
