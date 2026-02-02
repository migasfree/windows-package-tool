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

import ctypes
import errno
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import packaging.version

from .logging import logger
from .settings import (
    CONF_DIR,
    PKG_INFO_PATH,
    PKG_METADATA_FILE,
    PMS_DATA_PATH,
    PMS_PACKAGES_PATH,
    PMS_TEMP_PATH,
    SCRIPT_MAX_SIZE,
    STATUS_CURRENT,
    STATUS_DESIRED,
    STATUS_PATH,
)


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def check_app_dirs() -> None:
    locations = [PMS_DATA_PATH, PKG_INFO_PATH, PMS_TEMP_PATH, PMS_PACKAGES_PATH, CONF_DIR]
    for item in locations:
        if not os.path.exists(item):
            try:
                os.makedirs(item)
            except PermissionError:
                print(f'Insufficient permissions to create directory: {item}')
                sys.exit(errno.EACCES)
            except OSError:
                print(f'Problem creating app directory {item}')
                sys.exit(errno.EPERM)


def extract_tar_gz(file_path: str, name: str) -> None:
    with tarfile.open(file_path, 'r:gz') as tar:
        # filter argument added in Python 3.11.4 to address security concerns
        if sys.version_info >= (3, 11, 4):
            tar.extractall(path=name, filter='data')
        else:
            tar.extractall(path=name)


try:
    import msvcrt
except ImportError:
    import fcntl


_LOCK_HANDLE = None


def ensure_single_instance() -> None:
    """Ensure that only one instance of the application is running."""
    global _LOCK_HANDLE

    # Check permissions first, essentially checking if dirs exist
    check_app_dirs()

    try:
        from .settings import LOCK_FILE

        flags = os.O_RDWR | os.O_CREAT
        # We don't use O_TRUNC because we might want to read the PID potentially

        _LOCK_HANDLE = os.open(LOCK_FILE, flags, 0o666)

        if sys.platform == 'win32':
            # Lock the first byte
            msvcrt.locking(_LOCK_HANDLE, msvcrt.LK_NBLCK, 1)
        else:
            # POSIX flock
            fcntl.flock(_LOCK_HANDLE, fcntl.LOCK_EX | fcntl.LOCK_NB)

    except OSError as e:
        # Check if error is due to lock held
        if e.errno in (errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK):
            print('Another instance of the CLI is already running.')
            sys.exit(errno.ECANCELED)
        else:
            # Other error (e.g. permission denied)
            print(f'Could not acquire lock on {LOCK_FILE}: {e}')
            sys.exit(errno.EPERM)
    except Exception as e:
        print(f'Unexpected error acquiring lock: {e}')
        sys.exit(errno.EPERM)


def get_exec_file(file: str) -> Optional[str]:
    """Find executable script file with supported extension.

    Args:
        file: Base path to script (without extension)

    Returns:
        Full path to script if found, None otherwise
    """
    for ext in ('.py', '.cmd', '.ps1'):
        path = f'{file}{ext}'
        if os.path.exists(path):
            return path
    return None


def validate_script(script_file: str) -> bool:
    """Validate script before execution for security.

    Args:
        script_file: Path to the script file

    Raises:
        ValueError: If script fails validation
    """
    if not os.path.isfile(script_file):
        raise ValueError(f'Script file does not exist: {script_file}')

    file_size = os.path.getsize(script_file)
    if file_size > SCRIPT_MAX_SIZE:
        raise ValueError(f'Script file too large ({file_size} bytes, max {SCRIPT_MAX_SIZE})')

    # Ensure script is within the expected directory (prevent path traversal)
    if '..' in script_file:
        raise ValueError(f'Invalid script path (contains ..): {script_file}')

    return True


def run_script(script: str, timeout: Optional[int] = None, env: Optional[Dict[str, str]] = None) -> None:
    """Execute a maintainer script with security restrictions.

    Args:
        script: Base path to script (without extension)
        timeout: Execution timeout in seconds (default: from config)
        env: Environment variables to pass to the script

    Raises:
        RuntimeError: If script execution fails
        TimeoutError: If script exceeds timeout
        ValueError: If script fails validation
    """
    script_file = get_exec_file(script)
    if not script_file:
        return

    # Validate script before execution
    validate_script(script_file)

    if timeout is None:
        from .config import get_config

        timeout = get_config().script_timeout

    cmd = []
    if script_file.endswith('.cmd'):
        cmd = ['cmd', '/c', script_file]
    elif script_file.endswith('.ps1'):
        # Use RemoteSigned policy to prevent unsigned remote scripts
        cmd = ['powershell', '-ExecutionPolicy', 'RemoteSigned', '-File', script_file]
    elif script_file.endswith('.py'):
        cmd = ['python', script_file]

    if cmd:
        current_env = os.environ.copy()
        if env:
            current_env.update(env)

        logger.debug('Executing script command: %s', ' '.join(cmd))
        try:
            result = subprocess.run(  # noqa: UP022
                cmd,
                check=True,
                timeout=timeout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,  # noqa: UP021
                env=current_env,
            )
            if result.stdout:
                output = result.stdout.strip()
                logger.debug('Script output:\n%s', output)
                print(output)
        except subprocess.TimeoutExpired as e:
            raise TimeoutError(f'Script execution timed out after {timeout}s: {script_file}') from e
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            raise RuntimeError(f'Error executing script {script_file}: {error_msg}') from e


def verify_hash(file_: str, expected_hash: str) -> None:
    with open(file_, 'rb') as f:
        hash_ = hashlib.sha256(f.read()).hexdigest()

    if hash_ != expected_hash:
        raise ValueError('Hash mismatch')


def delete_files_with_pattern(directory: str, pattern: str) -> None:
    directory_path = Path(directory)
    if not directory_path.is_dir():
        print(f'Directory {directory} does not exist.')
        return

    pattern_path = directory_path / f'{pattern}*'

    files = glob.glob(str(pattern_path))

    for file in files:
        try:
            os.remove(file)
        except PermissionError:
            print(f'Insufficient permissions to delete: {file}')
        except OSError as e:
            print(f'Error deleting {file}: {e}')


def create_package_info(directory: str, package_name: str) -> None:
    pms_path = os.path.join(directory, package_name, 'pms')

    shutil.copy(
        os.path.join(pms_path, PKG_METADATA_FILE), os.path.join(PKG_INFO_PATH, f'{package_name}.{PKG_METADATA_FILE}')
    )

    scripts = ['preinst', 'install', 'postinst', 'prerm', 'remove', 'postrm']
    script_extensions = ['.ps1', '.cmd', '.py']
    for script in scripts:
        for script_extension in script_extensions:
            script_path = os.path.join(pms_path, f'{script}{script_extension}')
            if os.path.isfile(script_path):
                shutil.copy(script_path, os.path.join(PKG_INFO_PATH, f'{package_name}.{script}{script_extension}'))

    data_path = os.path.join(directory, package_name, 'data')
    if os.path.isdir(data_path):
        files = []
        for root, _, archives in os.walk(data_path):
            for item in [*archives, data_path]:
                if os.path.isfile(os.path.join(root, item)):
                    files.append(os.path.relpath(os.path.join(root, item), data_path))

        if files:
            with open(os.path.join(PKG_INFO_PATH, f'{package_name}.list'), 'w') as f:
                for item in sorted(files):
                    f.write(f'{item}\n')


def check_metadata_content(metadata: Dict[str, Any]) -> None:
    required_keys = ['name', 'version', 'maintainer', 'description', 'specification']
    for key in required_keys:
        if key not in metadata:
            raise ValueError(f'{PKG_METADATA_FILE} file does not contain the required key: {key}')

    if metadata['specification'] != '1.0.0':
        raise ValueError('specification key has an incorrect value. It must be "1.0.0"')

    if 'dependencies' in metadata:
        if not isinstance(metadata['dependencies'], list):
            raise ValueError('dependencies value is not a list')

        # Check if each dependency is in the expected format
        for dependency in metadata['dependencies']:
            match = re.match(r'^[a-zA-Z0-9_-]+(\s*\(([<>]=?|=)\s*([^)]+)\))?$', dependency)
            if not match:
                raise ValueError(f'dependency is not in the expected format: {dependency}')

            if match.group(3):
                try:
                    packaging.version.parse(match.group(3))
                except packaging.version.InvalidVersion:
                    raise ValueError(f'Invalid PEP 440 version in dependency: {dependency}') from None


def check_status_phases(desired: str, current: str) -> None:
    if desired not in STATUS_DESIRED:
        print(f'{desired} status has an incorrect value')
        sys.exit(errno.EINVAL)

    if current not in STATUS_CURRENT:
        print(f'{current} status has an incorrect value')
        sys.exit(errno.EINVAL)


def load_status() -> Dict[str, Any]:
    with open(STATUS_PATH) as f:
        return json.load(f)


def write_status(info: Dict[str, Any]) -> None:
    with open(STATUS_PATH, 'w') as f:
        json.dump(info, f, indent=2)


def update_package_status(name: str, version: str, desired: str, current: str, date: Optional[str] = None) -> None:
    check_status_phases(desired, current)

    status_info = load_status() if os.path.isfile(STATUS_PATH) else {}

    # Simplified: use setdefault pattern
    status_info.setdefault(name, {})[version] = {'status': {'desired': desired, 'current': current}}

    if date:
        if desired == 'i' and current == 'i':
            status_info[name][version]['install_date'] = date
        if desired == 'u' and current == 'n':
            status_info[name][version]['remove_date'] = date

    write_status(status_info)

    return status_info


def get_package_status(name: str) -> Optional[Dict[str, Any]]:
    if not os.path.isfile(STATUS_PATH):
        return None

    status_info = load_status()
    if name in status_info:
        return status_info[name]

    return None


def get_installed_package_status(name: str) -> Dict[str, Any]:
    if not os.path.isfile(STATUS_PATH):
        raise ValueError(f'Status info file {STATUS_PATH} does not exist')

    status_info = load_status()
    if name in status_info:
        for version, info in status_info[name].items():
            if info['status']['desired'] == 'i' and info['status']['current'] == 'i':
                return {version: info}

        raise ValueError(f'No installed version of package {name} found')
    else:
        raise ValueError(f'Package {name} not found in status info')


def is_package_installed(name: str, version: str) -> bool:
    status = get_package_status(name)
    if status is None or version not in status:
        return False

    return status[version]['status']['desired'] == 'i' and status[version]['status']['current'] == 'i'


def parse_dependency(dependency: str) -> Tuple[str, Optional[str]]:
    """
    Parses a dependency string in name and version string

    :param dependency: dependency string
    :return: Tuple with name and version string
    """
    if ' ' in dependency:
        dependency_name, dependency_version = dependency.split(' ', 1)
    else:
        dependency_name = dependency
        dependency_version = None

    return dependency_name, dependency_version


def parse_version(version: Optional[str]) -> Tuple[str, Optional[str]]:
    """
    Parses a version string in condition and version

    :param version: version string
    :return: tuple with condition and version
    """
    if not version or ' ' not in version:
        return '=', None

    condition, version = version.replace('(', '').replace(')', '').split(' ', 1)

    return condition, version


def check_version_condition(
    dependency_version: 'packaging.version.Version',
    condition: str,
    required_version: 'packaging.version.Version',
) -> bool:
    """Compare versions based on condition operator.

    Args:
        dependency_version: Version to check
        condition: Comparison operator ('=', '>', '<', '>=', '<=')
        required_version: Version to compare against

    Returns:
        True if condition is satisfied, False otherwise
    """
    ops = {
        '=': lambda a, b: a == b,
        '>': lambda a, b: a > b,
        '<': lambda a, b: a < b,
        '>=': lambda a, b: a >= b,
        '<=': lambda a, b: a <= b,
    }
    return ops.get(condition, lambda a, b: False)(dependency_version, required_version)


def check_dependency(
    name: str,
    installed_version: 'packaging.version.Version',
    condition: str,
    required_version: 'packaging.version.Version',
) -> bool:
    """Check if installed version satisfies the dependency condition.

    Args:
        name: Package name (for error messages)
        installed_version: Currently installed version
        condition: Comparison operator
        required_version: Required version

    Returns:
        True if dependency is satisfied

    Raises:
        ValueError: If dependency condition is not met
    """
    if not check_version_condition(installed_version, condition, required_version):
        condition_desc = {
            '=': f'version {required_version}',
            '>': f'version greater than {required_version}',
            '<': f'version less than {required_version}',
            '>=': f'version greater than or equal to {required_version}',
            '<=': f'version less than or equal to {required_version}',
        }.get(condition, f'{condition} {required_version}')
        raise ValueError(f'Dependency {name} has version {installed_version}, but {condition_desc} is required.')
    return True


def is_dependency_installed(
    name: str, condition: str, version: Optional[str], installed_packages: Dict[str, str]
) -> bool:
    """Check if a dependency is installed and satisfies version requirements.

    Args:
        name: Package name
        condition: Version comparison operator
        version: Required version (None if any version is acceptable)
        installed_packages: Dict of installed package names to versions

    Returns:
        True if dependency is satisfied, False otherwise
    """
    if name not in installed_packages:
        return False

    if version is None:
        return True

    installed_version = packaging.version.parse(installed_packages[name])
    required_version = packaging.version.parse(version)
    return check_dependency(name, installed_version, condition, required_version)
