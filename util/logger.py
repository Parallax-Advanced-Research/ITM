import enum
import time
import logging
import functools


class LogLevel(enum.IntEnum):
    CRITICAL = 50
    FATAL = CRITICAL
    ERROR = 40
    WARNING = 30
    WARN = WARNING
    INFO = 20
    DEBUG = 10
    NOTSET = 0


def _tagged_log(self, level, msg, *args, **kwargs):
    if 'tag' in kwargs:
        tag = kwargs['tag']
        del kwargs['tag']

        if tag in logger._tags:
            ctime = time.time()
            elapsed = ctime - logger._tags[tag]
            msg += f" [{elapsed:.4f}s]"
            logger._tags[tag] = ctime
        else:
            logger._tags[tag] = time.time()
    logging.Logger._log(self, level, msg, *args, **kwargs, stacklevel=2)


class CustomFormatter(logging.Formatter):
    grey = "\x1b[30;2m"
    blue = "\x1b[36;1m"
    green = "\x1b[32;1m"
    yellow = "\x1b[33;21m"
    red = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(levelname)s: %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: blue + format + reset,
        logging.INFO: green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class SimpleFormatter(logging.Formatter):
    format_str = "%(levelname)s: %(message)s (%(filename)s:%(lineno)d)"

    def format(self, record):
        formatter = logging.Formatter(self.format_str)
        return formatter.format(record)


logger = logging.getLogger("TAD")
logger.setLevel(logging.DEBUG)
logger._log = functools.partial(_tagged_log, logger)
logger._tags = {}

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(CustomFormatter())
logger.addHandler(ch)
logger.propagate = False


def use_simple_logger():
    ch.setFormatter(CustomFormatter())
