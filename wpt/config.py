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

"""Configuration management for Windows Package Tool.

This module provides INI-based configuration with conf.d directory support.
Configuration files are loaded in this order:
1. Main config file (wpt.conf)
2. Files in conf.d/ directory (alphabetically sorted)

Later values override earlier ones.
"""

import configparser
import logging
import os
import shutil

# Default configuration values
DEFAULTS = {
    'logging': {
        'level': 'INFO',
    },
    'ssl': {
        'verify': 'true',
    },
    'scripts': {
        'timeout': '300',
    },
}


def _get_package_conf_dir():
    """Get the path to the conf directory bundled with the package.

    Returns:
        str: Path to the package's conf directory
    """
    # The conf directory is at the same level as the wpt package
    package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(package_dir, 'conf')


def _ensure_config_files(config_file, conf_dir):
    """Ensure configuration files exist, copying from package if needed.

    Args:
        config_file: Path to main configuration file
        conf_dir: Path to conf.d directory
    """
    import contextlib

    # Get the package's example config directory
    package_conf_dir = _get_package_conf_dir()
    package_conf_file = os.path.join(package_conf_dir, 'wpt.conf')

    # Create conf.d directory if it doesn't exist
    if not os.path.isdir(conf_dir):
        with contextlib.suppress(OSError):
            os.makedirs(conf_dir, exist_ok=True)

    # Copy example config if it doesn't exist and package config is available
    if not os.path.isfile(config_file) and os.path.isfile(package_conf_file):
        with contextlib.suppress(OSError, shutil.Error):
            # Ensure parent directory exists
            parent_dir = os.path.dirname(config_file)
            if not os.path.isdir(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)

            shutil.copy2(package_conf_file, config_file)


def _str_to_bool(value):
    """Convert string to boolean.

    Args:
        value: String value to convert

    Returns:
        bool: Converted boolean value
    """
    if isinstance(value, bool):
        return value

    if str(value).lower() in ('true', 'yes', 'on', '1'):
        return True
    if str(value).lower() in ('false', 'no', 'off', '0'):
        return False

    raise ValueError(f'Cannot convert {value!r} to bool')


def _str_to_log_level(value):
    """Convert string to logging level.

    Args:
        value: String value (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        int: Logging level constant
    """
    levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
    }

    upper_value = str(value).upper()
    if upper_value in levels:
        return levels[upper_value]

    raise ValueError(f'Invalid log level: {value}')


class Config:
    """Configuration container with typed accessors."""

    def __init__(self, config_file, conf_dir):
        """Initialize configuration.

        Args:
            config_file: Path to main configuration file
            conf_dir: Path to conf.d directory
        """
        self._config_file = config_file
        self._conf_dir = conf_dir
        self._parser = configparser.ConfigParser()
        self._load_defaults()
        self._load_config()

    def _load_defaults(self):
        """Load default configuration values."""
        for section, values in DEFAULTS.items():
            if not self._parser.has_section(section):
                self._parser.add_section(section)
            for key, value in values.items():
                self._parser.set(section, key, value)

    def _load_config(self):
        """Load configuration from files."""
        # Load main config file if exists
        if os.path.isfile(self._config_file):
            self._parser.read(self._config_file, encoding='utf-8')

        # Load conf.d files in alphabetical order
        if os.path.isdir(self._conf_dir):
            conf_files = sorted(f for f in os.listdir(self._conf_dir) if f.endswith('.conf'))
            for conf_file in conf_files:
                conf_path = os.path.join(self._conf_dir, conf_file)
                if os.path.isfile(conf_path):
                    self._parser.read(conf_path, encoding='utf-8')

    def get(self, section, key, fallback=None):
        """Get a configuration value.

        Args:
            section: Configuration section
            key: Configuration key
            fallback: Fallback value if not found

        Returns:
            Configuration value or fallback
        """
        try:
            return self._parser.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback

    def getboolean(self, section, key, fallback=None):
        """Get a boolean configuration value.

        Args:
            section: Configuration section
            key: Configuration key
            fallback: Fallback value if not found

        Returns:
            bool: Configuration value or fallback
        """
        value = self.get(section, key)
        if value is None:
            return fallback
        return _str_to_bool(value)

    def getint(self, section, key, fallback=None):
        """Get an integer configuration value.

        Args:
            section: Configuration section
            key: Configuration key
            fallback: Fallback value if not found

        Returns:
            int: Configuration value or fallback
        """
        value = self.get(section, key)
        if value is None:
            return fallback
        return int(value)

    @property
    def log_level(self):
        """Get logging level.

        Returns:
            int: Logging level constant (e.g., logging.DEBUG)
        """
        value = self.get('logging', 'level', 'INFO')
        return _str_to_log_level(value)

    @property
    def ssl_verify(self):
        """Get SSL verification setting.

        Returns:
            bool or str: True/False for verification, or path to CA bundle
        """
        value = self.get('ssl', 'verify', 'true')

        # Check if it's a path to a CA bundle
        if os.path.isfile(value):
            return value

        # Otherwise, treat as boolean
        return _str_to_bool(value)

    @property
    def script_timeout(self):
        """Get script execution timeout in seconds.

        Returns:
            int: Timeout in seconds (default: 300)
        """
        return self.getint('scripts', 'timeout', 300)

    def as_dict(self):
        """Export configuration as dictionary.

        Returns:
            dict: Configuration as nested dictionary
        """
        result = {}
        for section in self._parser.sections():
            result[section] = dict(self._parser.items(section))
        return result


# Global configuration instance (lazy loaded)
_config = None


def get_config(config_file=None, conf_dir=None):
    """Get or create the global configuration instance.

    Args:
        config_file: Optional path to main config file
        conf_dir: Optional path to conf.d directory

    Returns:
        Config: Global configuration instance
    """
    global _config

    if _config is None:
        # Import here to avoid circular imports
        from .settings import CONF_DIR, CONF_FILE

        config_file = config_file or CONF_FILE
        conf_dir = conf_dir or CONF_DIR

        # Ensure config files exist (copy from package if needed)
        _ensure_config_files(config_file, conf_dir)

        _config = Config(config_file, conf_dir)

    return _config


def reload_config():
    """Reload configuration from disk.

    Returns:
        Config: New configuration instance
    """
    global _config
    _config = None
    return get_config()
