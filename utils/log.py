import sys
import logging
from types import FrameType
from typing import cast
from loguru import logger

class Logger:
    def __init__(self):
        self.logger = logger
        self.logger.remove()
        self.logger.add(sys.stdout,
                        format="<green>{time:YYYYMMDD HH:mm:ss}</green> | "
                               "{process.name} | "
                               "{thread.name} | "
                               "<cyan>{module}</cyan>.<cyan>{function}</cyan>"
                               ":<cyan>{line}</cyan> | "
                               "<level>{level}</level>: "
                               "<level>{message}</level>",
                        )

    def init_config(self):
        LOGGER_NAMES = ("uvicorn.asgi", "uvicorn.access", "uvicorn")
 
        # change handler for default uvicorn logger
        logging.getLogger().handlers = [InterceptHandler()]
        for logger_name in LOGGER_NAMES:
            logging_logger = logging.getLogger(logger_name)
            logging_logger.handlers = [InterceptHandler()]

    def get_logger(self):
        return self.logger

class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)
 
        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:  # noqa: WPS609
            frame = cast(FrameType, frame.f_back)
            depth += 1
 
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

Loggers = Logger()
log = Loggers.get_logger()
