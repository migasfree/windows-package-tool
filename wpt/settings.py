# Copyright (c) 2024-2026 Jose Antonio Chavarría <jachavar@gmail.com>
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

import os
import sys
import tempfile

from rich.theme import Theme

# Semantic CLI Theme
THEME = Theme(
    {
        'info': 'bold blue',
        'success': 'bold green',
        'warning': 'bold yellow',
        'error': 'bold red',
        'header': 'bold magenta',
        'text.inverse': 'reverse',
        # Domain specific
        'pkg.name': 'cyan',
        'pkg.version': 'green',
        'url': 'underline cyan',
    }
)

PROGRAM = 'Windows Package Tool'
PROGRAM_DESC = f'{PROGRAM}: A simple package management system'

PMS = 'wpt'


def _get_data_path():
    """Get validated data path for the application.

    Returns:
        str: Absolute path to the application data directory

    The function validates PROGRAMDATA environment variable and provides
    fallbacks for non-Windows systems or misconfigured environments.
    """
    # Try PROGRAMDATA first (standard Windows location)
    programdata = os.getenv('PROGRAMDATA')

    if programdata:
        # Validate it's an absolute path and exists
        if os.path.isabs(programdata) and os.path.isdir(programdata):
            return os.path.join(programdata, PMS)

        # Log warning but don't fail (will use fallback)
        if not os.path.isabs(programdata):
            print(f'Warning: PROGRAMDATA is not an absolute path: {programdata}', file=sys.stderr)
        else:
            print(f'Warning: PROGRAMDATA directory does not exist: {programdata}', file=sys.stderr)

    # Fallback for non-Windows or misconfigured systems
    # Use user's local app data or home directory
    if sys.platform == 'win32':
        # Try LOCALAPPDATA as fallback on Windows
        localappdata = os.getenv('LOCALAPPDATA')
        if localappdata and os.path.isabs(localappdata):
            return os.path.join(localappdata, PMS)

        # Last resort: user's home directory
        return os.path.join(os.path.expanduser('~'), f'.{PMS}')
    else:
        # Unix-like systems: use XDG_DATA_HOME or ~/.local/share
        xdg_data = os.getenv('XDG_DATA_HOME')
        if xdg_data and os.path.isabs(xdg_data):
            return os.path.join(xdg_data, PMS)

        return os.path.join(os.path.expanduser('~'), '.local', 'share', PMS)


PMS_DATA_PATH = _get_data_path()
PMS_TEMP_PATH = os.path.join(PMS_DATA_PATH, 'temp')

# Configuration paths
CONF_FILE = os.path.join(PMS_DATA_PATH, 'wpt.conf')
CONF_DIR = os.path.join(PMS_DATA_PATH, 'conf.d')

PKG_METADATA_FILE = 'metadata.json'
PKG_INFO_PATH = os.path.join(PMS_DATA_PATH, 'info')
PKG_ARCH = 'x64'
PKG_EXT = '.tar.gz'

SOURCES = 'sources.list'
SOURCES_PATH = os.path.join(PMS_DATA_PATH, SOURCES)

REPO_FILE = 'packages.json'
REPO_LOCAL_PATH = os.path.join(PMS_DATA_PATH, REPO_FILE)

STATUS_PATH = os.path.join(PMS_DATA_PATH, 'status.json')
STATUS_DESIRED = {
    'u': 'unknown',
    'i': 'marked for installation',
    'r': 'marked for removal',
}
STATUS_CURRENT = {
    'n': 'not installed',
    'i': 'successfully installed',
    'u': 'unpacked',
    'h': 'partially installed',
}

# Script execution security settings
SCRIPT_MAX_SIZE = 1024 * 1024  # 1MB max script size

# Logging settings
LOG_FILE = os.path.join(tempfile.gettempdir(), 'wpt.log')
LOG_MAX_SIZE = 5 * 1024 * 1024  # 5MB
LOG_BACKUP_COUNT = 3
LOG_FORMAT = '%(asctime)s [%(levelname)s] %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
