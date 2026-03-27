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

"""GPG signature verification utilities for Windows Package Tool."""

import logging
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


def verify_signature(file_path: str, sig_path: str) -> bool:
    """
    Verifies a GPG detached signature.

    Args:
        file_path: Path to the file to verify
        sig_path: Path to the signature file (.sig)

    Returns:
        True if signature is valid, False otherwise
    """
    try:
        result = subprocess.run(  # noqa: UP022
            ['gpg', '--verify', sig_path, file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,  # noqa: UP021
            check=True,
        )
        logger.debug('GPG verification output: %s', result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        logger.warning('GPG verification failed: %s', e.stderr)
        return False
    except FileNotFoundError:
        logger.warning('GPG not available on this system')
        return False


def import_key(key_path: str) -> bool:
    """
    Imports a GPG public key.

    Args:
        key_path: Path to the public key file

    Returns:
        True if import succeeded, False otherwise
    """
    try:
        result = subprocess.run(  # noqa: UP022
            ['gpg', '--import', key_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,  # noqa: UP021
            check=True,
        )
        logger.info('GPG key imported successfully')
        logger.debug('GPG import output: %s', result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        logger.error('Failed to import GPG key: %s', e.stderr)
        return False
    except FileNotFoundError:
        logger.error('GPG not available on this system')
        return False


def get_key_info(key_path: str) -> Optional[str]:
    """
    Gets information about a GPG key file.

    Args:
        key_path: Path to the public key file

    Returns:
        Key fingerprint/info or None if failed
    """
    try:
        result = subprocess.run(  # noqa: UP022
            ['gpg', '--with-fingerprint', '--with-colons', key_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,  # noqa: UP021
            check=True,
        )
        return result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
