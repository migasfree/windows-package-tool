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

"""Exit code constants for Windows Package Tool."""

import errno
import sys

# Common Exit Codes
SUCCESS = 0

if sys.platform == 'win32':
    # Windows System Error Codes
    # Reference: https://learn.microsoft.com/en-us/windows/win32/debug/system-error-codes--0-499-
    PERM = 5  # ERROR_ACCESS_DENIED
    NOT_FOUND = 2  # ERROR_FILE_NOT_FOUND
    CANCELED = 1223  # ERROR_CANCELLED
    FAILURE = 1  # ERROR_INVALID_FUNCTION / General failure
else:
    # POSIX equivalents
    PERM = getattr(errno, 'EPERM', 1)
    NOT_FOUND = getattr(errno, 'ENOENT', 2)
    CANCELED = getattr(errno, 'ECANCELED', 125)
    FAILURE = 1
