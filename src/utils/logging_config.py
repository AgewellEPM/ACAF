# src/utils/logging_config.py
# Centralized logging configuration for the Worker Mind project.

import logging
import os
from datetime import datetime
from config import AppConfig # Import AppConfig for logging level and file path

def setup_logging():
    """
    Sets up a standardized logging configuration for the application.
    Logs messages to both console and a file.
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(AppConfig.LOG_FILE_PATH)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_level = getattr(logging, AppConfig.LOG_LEVEL.upper(), logging.INFO)

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers to prevent duplicate logs if called multiple times
    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)

    # Console Handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File Handler
    file_handler = logging.FileHandler(AppConfig.LOG_FILE_PATH)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    logging.info("Logging configured successfully.")

# Example usage in other modules:
# from utils.logging_config import setup_logging
# setup_logging() # Call once at application start
# import logging
# logger = logging.getLogger(__name__)
# logger.info("This is an info message from a module.")
