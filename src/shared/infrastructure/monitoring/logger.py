"""Logging configuration utilizing Loguru for structured, beautiful, and unified application logs.

Intercepts standard library logging (e.g., from FastAPI, Uvicorn, SQLAlchemy) and forwards
them to Loguru. Supports colorized console output and structured log file persistence.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Union

from loguru import logger


class InterceptHandler(logging.Handler):
    """Custom standard logging handler to redirect logs to Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists
        try:
            level: Union[str, int] = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame = logging.currentframe()
        depth = 0
        while frame:
            filename = frame.f_code.co_filename
            # Walk up to skip frames inside this logger config and the logging standard library
            if "logger.py" in filename or filename == logging.__file__ or "logging/__init__.py" in filename or frame.f_globals.get("__name__", "").startswith("logging"):
                frame = frame.f_back
                depth += 1
            else:
                break

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def log_filter(record: dict[str, Any]) -> bool:
    """Filter function to keep logs clean and reduce third-party noise.

    - Allows all INFO and higher logs except for known extremely noisy loggers.
    - Only allows DEBUG level logs if they originate from K.I.R.A project ('src').
    """
    level_name = record["level"].name
    module_name = record["name"]

    # Suppress files/directories file-watching logs completely as they trigger on git changes
    if "watchfiles" in module_name or "watchdog" in module_name:
        return False

    # For DEBUG logs, only allow our own codebase (starts with 'src')
    if level_name == "DEBUG":
        return module_name.startswith("src")

    return True


def setup_logging(debug: bool = True, log_file_path: Union[str, Path] = "logs/kira.log") -> None:
    """Configure unified logging with Loguru.

    Interceptors are set up for standard library loggers so all components
    share the same formatting and outputs.

    Args:
        debug: If True, sets logging level to DEBUG. Otherwise, INFO.
        log_file_path: Relative or absolute path to write persistent log files.
    """
    log_level = "DEBUG" if debug else "INFO"

    # Define console format with high readability and colors
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    # Define file format (no ANSI escape codes for file)
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "{name}:{function}:{line} - "
        "{message}"
    )

    # Configure Loguru sinks
    config: dict[str, Any] = {
        "handlers": [
            {
                "sink": sys.stderr,
                "level": log_level,
                "format": console_format,
                "colorize": True,
                "filter": log_filter,
            }
        ]
    }

    # Add file sink for persistence
    if log_file_path:
        log_file = Path(log_file_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        config["handlers"].append(
            {
                "sink": str(log_file),
                "level": "INFO",  # Keep file logs to INFO to avoid excessive dev debugging clutter
                "format": file_format,
                "rotation": "10 MB",
                "retention": "10 days",
                "compression": "zip",
                "filter": log_filter,
            }
        )

    logger.configure(**config)

    # Intercept all logging.root logs
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(logging.NOTSET)

    # Intercept specific standard library loggers and clear their handlers
    loggers_to_intercept = [
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "fastapi",
        "sqlalchemy",
        "sqlalchemy.engine",
        "qdrant_client",
        "httpx",
        "httpcore",
        "watchfiles",
        "watchdog",
    ]

    for logger_name in loggers_to_intercept:
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False

    # Adjust external noisy logs to prevent flooding
    if debug:
        # Mute connection pool, HTTP requests, and file watching noise
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("qdrant_client").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("watchfiles").setLevel(logging.WARNING)
        logging.getLogger("watchdog").setLevel(logging.WARNING)
        logging.getLogger("openai").setLevel(logging.WARNING)
        logging.getLogger("anthropic").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("asyncio").setLevel(logging.WARNING)
    else:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.ERROR)
        logging.getLogger("qdrant_client").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("watchfiles").setLevel(logging.ERROR)
        logging.getLogger("watchdog").setLevel(logging.ERROR)
        logging.getLogger("openai").setLevel(logging.WARNING)
        logging.getLogger("anthropic").setLevel(logging.WARNING)

    logger.info(f"Unified logging initialized using Loguru. Level: {log_level}")
