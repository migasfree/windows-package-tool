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
import os
from logging.handlers import RotatingFileHandler

from .settings import (
    LOG_BACKUP_COUNT,
    LOG_DATE_FORMAT,
    LOG_FILE,
    LOG_FORMAT,
    LOG_MAX_SIZE,
    PMS_DATA_PATH,
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
        logger.setLevel(logging.DEBUG)

        # Ensure log directory exists
        os.makedirs(PMS_DATA_PATH, exist_ok=True)

        # File handler with rotation
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=LOG_MAX_SIZE,
            backupCount=LOG_BACKUP_COUNT,
            encoding='utf-8',
        )
        file_handler.setLevel(logging.DEBUG)
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
