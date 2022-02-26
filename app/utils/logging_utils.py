import logging
from app.config import Config

# Code taken from
# https://stackoverflow.com/questions/14844970/modifying-logging-message-format-based-on-message-logging-level-in-python3

# Attempt to set up a Python3 logger than will print custom messages
# based on each message's logging level.
# The technique recommended for Python2 does not appear to work for
# Python3


class CustomConsoleFormatter(logging.Formatter):
    """
    Modify the way DEBUG messages are displayed.

    """
    # def __init__(self, fmt="%(levelno)d: %(msg)s"):
    #     logging.Formatter.__init__(self, fmt=fmt)

    def format(self, record):

        # Remember the original format
        format_orig = self._style._fmt

        if record.levelno == logging.DEBUG:
            self._style._fmt = Config.LOGGING_FORMAT_DEBUG
        if record.levelno == logging.INFO:
            self._style._fmt = Config.LOGGING_FORMAT_INFO

        # Call the original formatter to do the grunt work
        result = logging.Formatter.format(self, record)

        # Restore the original format
        self._style._fmt = format_orig

        return result


def get_logger(name):
    my_logger = logging.getLogger(name)
    my_logger.setLevel(Config.LOGGING_LEVEL)

    my_formatter = CustomConsoleFormatter()

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(my_formatter)

    my_logger.addHandler(console_handler)

    return my_logger
