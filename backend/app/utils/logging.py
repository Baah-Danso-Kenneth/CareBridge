import logging
import sys

def setup_logging(level=logging.INFO):
    """Centralized logging configuration."""

    logger = logging.getLogger()
    logger.setLevel(level)

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    console.setFormatter(formatter)
    logger.addHandler(console)

    #File handler for audit 
    file_handler = logging.FileHandler('logs/carebridge.log')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger



logger = setup_logging()