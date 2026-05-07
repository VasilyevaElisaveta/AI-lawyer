import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


class ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[37m",     # серый
        "INFO": "\033[36m",      # голубой
        "WARNING": "\033[33m",   # жёлтый
        "ERROR": "\033[31m",     # красный
        "CRITICAL": "\033[41m",  # красный фон
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        color = self.COLORS.get(record.levelname, self.RESET)
        return f"{color}{message}{self.RESET}"


class LoggerFactory:
    _loggers: dict[str, logging.Logger] = {}

    @staticmethod
    def get_logger(
        name: str,
        *,
        logs_path: str = "logs",
        log_file: str | None = None,
        console_level: int = logging.DEBUG,
        file_level: int = logging.INFO,
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5,
    ) -> logging.Logger:
        if name in LoggerFactory._loggers:
            return LoggerFactory._loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        if not logger.handlers:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(console_level)
            console_handler.setFormatter(
                ColoredFormatter(
                    fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                    datefmt="%H:%M:%S",
                )
            )
            logger.addHandler(console_handler)

            if log_file is not None:
                Path(logs_path).mkdir(parents=True, exist_ok=True)
                file_handler = RotatingFileHandler(
                    Path(logs_path) / log_file,
                    maxBytes=max_bytes,
                    backupCount=backup_count,
                    encoding="utf-8",
                )
                file_handler.setLevel(file_level)
                file_handler.setFormatter(
                    logging.Formatter(
                        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S",
                    )
                )
                logger.addHandler(file_handler)

        LoggerFactory._loggers[name] = logger
        return logger