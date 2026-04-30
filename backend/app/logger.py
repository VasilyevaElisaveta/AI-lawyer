import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from dotenv import load_dotenv
from os import getenv


load_dotenv()



def setup_logger() -> logging.Logger:
    logger = logging.getLogger("app")
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s |  BACKEND | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    logs_path = getenv("logs_path", "logs")
    Path(logs_path).mkdir(exist_ok=True)
    file_handler = RotatingFileHandler(
        f"{logs_path}/backend.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger

logger = setup_logger()
