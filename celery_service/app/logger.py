
"""Utils connected with logging."""

import logging


def get_logger(mod_name):
    """Configure logger and return."""
    logger = logging.getLogger(mod_name)
    logger.propagate = False
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s [%(name)-12s] %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
