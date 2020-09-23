class Error(Exception):
    pass


class ConfigError(Error):
    def __init__(self, config_option, message):
        self.config_option = config_option
        self.message = message
