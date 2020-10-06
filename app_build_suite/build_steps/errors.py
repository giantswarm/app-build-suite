"""Errors returned by app_build_suite"""


class Error(Exception):
    """
    Basic error class that just returns a message.
    """

    msg: str


class ConfigError(Error):
    """
    Error class that shows error in configuration options.
    """

    config_option: str

    def __init__(self, config_option, message):
        self.config_option = config_option
        self.msg = message


class ValidationError(Error):
    """
    ValidationError means some input data (configuration, chart) is impossible to process or fails
    assumptions.
    """

    source: str

    def __init__(self, source, message):
        self.source = source
        self.msg = message


class BuildError(Error):
    """
    BuildError can be raised only during executing actual build process (not configuration or validation).
    """

    source: str

    def __init__(self, source, message):
        self.source = source
        self.msg = message
