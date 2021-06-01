from step_exec_lib.errors import Error


class BuildError(Error):
    """
    BuildError can be raised only during executing actual build process (not configuration or validation).
    """

    source: str

    def __init__(self, source: str, message: str):
        super().__init__(message)
        self.source = source

    def __str__(self) -> str:
        return f"Source: '{self.source}', message: {self.msg}."
