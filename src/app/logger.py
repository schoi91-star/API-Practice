"""
Logging configuration module.

Wraps Python's logging module to provide consistent log format
and level settings across the application.

Usage:
    # At app startup (in run_session_metrics.py)
    logger = setup_logger("app", level=logging.DEBUG)

    # In each module
    from .logger import get_logger
    logger = get_logger(__name__)
    logger.info("message")
"""
import logging
import sys


def setup_logger(
    name: str = "app",
    level: int = logging.INFO,
    log_format: str | None = None,
) -> logging.Logger:
    """
    Configure and return a logger instance.

    Args:
        name: Logger name. Usually "app" or module's __name__
        level: Logging level
            - logging.DEBUG: All messages (detailed dev info)
            - logging.INFO: General info messages
            - logging.WARNING: Warning messages
            - logging.ERROR: Error messages
            - logging.CRITICAL: Critical errors
        log_format: Custom format string (use default if None)

    Returns:
        Configured Logger instance

    Example:
        # Basic usage
        logger = setup_logger("app")

        # Debug mode
        logger = setup_logger("app", level=logging.DEBUG)
    """
    # Default format: "2024-01-15 10:30:00 [INFO] app.module: message"
    if log_format is None:
        log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    logger = logging.getLogger(name)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Add handler that outputs to stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S"))

    logger.addHandler(handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance by name.

    Should be called after setup_logger() has been invoked.
    Use this to get a logger in each module.

    Args:
        name: Logger name. Usually pass __name__

    Returns:
        Logger instance

    Example:
        # At module top level
        logger = get_logger(__name__)

        # Inside functions
        logger.info("Starting task")
        logger.debug(f"Details: {data}")
        logger.error(f"Error occurred: {e}")
    """
    return logging.getLogger(name)
