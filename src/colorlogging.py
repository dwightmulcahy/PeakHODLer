import logging
import os
from logging.handlers import RotatingFileHandler
import colorlog
import sys

# File handler config
MAX_BYTES = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 2

# ========== Logging Configuration ==========
def setup_logging(app_name: str, log_level=logging.INFO):
    """
    Configures the application's logging with colorized console output
    and file logging, ensuring consistent content formatting.

    Returns:
        logger (logging.Logger): The logger instance for the current module.
        log_file_path (str): Full path to the log file.
    """

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # IMPORTANT: Clear existing handlers to prevent duplicates if called multiple times
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Define formatting
    base_format = '%(levelname)-8s | %(asctime)s | %(filename)s:%(lineno)d | %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # File Handler Setup
    log_dir_name = app_name.replace(" ", "_").lower()
    log_dir = os.path.join(os.path.expanduser('~'), 'Library', 'Logs', log_dir_name)
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, f'{app_name}.log')

    # Conditionally clear the log file (only in non-production environments)
    if os.environ.get("ENV", "dev") != "production":
        try:
            with open(log_file_path, 'w', encoding="utf-8"):
                pass # opening the file with 'w' overwrites the file
            sys.stderr.write(f"[INFO] Log file '{log_file_path}' cleared on app start.\n")
        except Exception as e:
            sys.stderr.write(f"[ERROR] Failed to clear log file '{log_file_path}': {e}\n")

    file_handler = RotatingFileHandler(
        log_file_path, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    file_formatter = logging.Formatter(base_format, datefmt=date_format)
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)

    # Console Handler with Color
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    color_formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(levelname)-8s%(reset)s | %(asctime)s | %(filename)s:%(lineno)d | %(bold_white)s%(message)s',
        datefmt=date_format,
        log_colors={
            'DEBUG':    'cyan',
            'INFO':     'green',
            'WARNING':  'yellow',
            'ERROR':    'red',
            'CRITICAL': 'bold_red,bg_white',
        },
        secondary_log_colors={
            'message': {
                'ERROR': 'red',
                'CRITICAL': 'bold_red',
            }
        },
        style='%'
    )
    console_handler.setFormatter(color_formatter)
    root_logger.addHandler(console_handler)

    logger = logging.getLogger(__name__)
    logger.info("Color console logging configured.")
    logger.info(f"File logging to {log_file_path}.")

    return logger, log_file_path
