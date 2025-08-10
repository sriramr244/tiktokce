import logging


def setup_logger(
    name: str = "social_content_engine",
    log_file: str = "social_content_engine.log",
    level=logging.INFO,
):
    """
    Get a logger with a specified name, log file, and logging level.

    Args:
        name (str): The name of the logger. Defaults to "social_content_engine".
        log_file (str): The file to which logs should be written. Defaults to "social_content_engine.log".
        level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Defaults to logging.INFO.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)

    # Set the logging level
    logger.setLevel(level)

    # Create handlers if they are not already added
    if not logger.hasHandlers():
        c_handler = logging.StreamHandler()
        f_handler = logging.FileHandler(log_file)
        c_handler.setLevel(logging.WARNING)
        f_handler.setLevel(level)

        # Create formatters and add it to handlers
        c_format = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
        f_format = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        c_handler.setFormatter(c_format)
        f_handler.setFormatter(f_format)

        # Add handlers to the logger
        logger.addHandler(c_handler)
        logger.addHandler(f_handler)

    return logger


# Create a global logger instance
logger = setup_logger()
