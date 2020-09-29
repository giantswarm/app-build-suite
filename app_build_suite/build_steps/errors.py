class Error(Exception):
    msg: str


class ConfigError(Error):
    config_option: str

    def __init__(self, config_option, message):
        self.config_option = config_option
        self.msg = message


class ValidationError(Error):
    source: str

    def __init__(self, source, message):
        self.source = source
        self.msg = message


class BuildError(Error):
    source: str

    def __init__(self, source, message):
        self.source = source
        self.msg = message
