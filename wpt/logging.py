# Copyright (c) 2026 Jose Antonio Chavarría <jachavar@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""Logging configuration for Windows Package Tool."""

import logging
from logging.handlers import RotatingFileHandler

from .config import get_config
from .settings import (
    LOG_BACKUP_COUNT,
    LOG_DATE_FORMAT,
    LOG_FILE,
    LOG_FORMAT,
    LOG_MAX_SIZE,
)


def get_logger(name: str = 'wpt') -> logging.Logger:
    """Get a configured logger instance.

    Args:
        name: Logger name (default: 'wpt')

    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        config = get_config()
        log_level = config.log_level

        logger.setLevel(log_level)

        # File handler with rotation
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=LOG_MAX_SIZE,
            backupCount=LOG_BACKUP_COUNT,
            encoding='utf-8',
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
        logger.addHandler(file_handler)

        # Console handler for user-facing messages
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(console_handler)

    return logger


# Global logger instance
logger: logging.Logger = get_logger()


def configure_logging(quiet: bool = False, debug: bool = False) -> None:
    """Dynamically adjust logging configuration based on CLI arguments.

    Args:
        quiet: If True, suppress console log output.
        debug: If True, enable debug output to console with detailed formatting.
    """
    logger = logging.getLogger('wpt')

    # Ensure handlers are initialized first
    if not logger.handlers:
        get_logger('wpt')

    if debug:
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)
            # Use detailed formatter for stream/console handler
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, RotatingFileHandler):
                handler.setFormatter(
                    logging.Formatter(
                        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        datefmt=LOG_DATE_FORMAT,
                    )
                )
    elif quiet:
        # Silence console handler completely
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, RotatingFileHandler):
                handler.setLevel(logging.CRITICAL + 1)
    else:
        # Reset to defaults
        config = get_config()
        log_level = config.log_level
        logger.setLevel(log_level)
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, RotatingFileHandler):
                handler.setLevel(logging.INFO)
                handler.setFormatter(logging.Formatter('%(message)s'))
            else:
                handler.setLevel(log_level)
