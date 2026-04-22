import logging
import sys


class ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[37m",     # серый
        "INFO": "\033[36m",      # голубой
        "WARNING": "\033[33m",   # жёлтый
        "ERROR": "\033[31m",     # красный
        "CRITICAL": "\033[41m",  # красный фон
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        message = super().format(record)
        return f"{color}{message}{self.RESET}"
    

class LoggerFactory:
    _loggers = {}

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        if name in LoggerFactory._loggers:
            return LoggerFactory._loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)

        formatter = ColoredFormatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%H:%M:%S"
        )

        handler.setFormatter(formatter)

        logger.addHandler(handler)
        logger.propagate = False

        LoggerFactory._loggers[name] = logger
        return logger