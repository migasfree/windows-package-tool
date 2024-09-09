# Copyright (c) 2024 Jose Antonio Chavarría <jachavar@gmail.com>
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

PROGRAM = 'Windows Package Tool'
PROGRAM_DESC = f'{PROGRAM}: A simple package management system'

PMS = 'wpt'
PMS_DATA_PATH = os.path.join(os.getenv('PROGRAMDATA', ''), PMS)
PMS_TEMP_PATH = os.path.join(PMS_DATA_PATH, 'temp')

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
