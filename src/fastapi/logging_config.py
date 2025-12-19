# logging_config.py

import logging
import logging.config
import os

if not os.path.exists("logs"):
    os.mkdir("logs")


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "verbose": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - "
            "%(message)s [%(filename)s:%(lineno)s]",
        },
        "simple": {
            "format": "%(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": "logs/app.log",
            "formatter": "verbose",
        },
        "error_file": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": "logs/error.log",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "fastapi": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": True,
        },
        "uvicorn": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": True,
        },
        "app": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "errors": {
            "level": "ERROR",
            "handlers": ["error_file"],
            "propagate": False,
        },
    },
    "root": {"level": "INFO", "handlers": ["console", "file"]},
}


def setup_logging():
    logging.config.dictConfig(LOGGING_CONFIG)
