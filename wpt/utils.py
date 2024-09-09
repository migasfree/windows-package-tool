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
import sys
import subprocess
import shutil
import hashlib
import json
import glob
import re
import ctypes
import tarfile
import errno
import packaging.version
try:
    import wmi
except ImportError:
    pass

from pathlib import Path

from .settings import (
    PKG_METADATA_FILE, PKG_INFO_PATH,
    PMS_DATA_PATH, PMS_TEMP_PATH,
    STATUS_PATH, STATUS_DESIRED, STATUS_CURRENT,
)


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def check_app_dirs():
    locations = [PMS_DATA_PATH, PKG_INFO_PATH, PMS_TEMP_PATH]
    for item in locations:
        if not os.path.exists(item):
            try:
                os.makedirs(item)
            except OSError:
                print(f'Problem creating app directory {item}')
                sys.exit(errno.EPERM)
            except PermissionError:
                print(f'Insufficient permissions to create directory: {item}')
                sys.exit(errno.EACCES)


def extract_tar_gz(file_path, name):
    with tarfile.open(file_path, 'r:gz') as tar:
        tar.extractall(path=name)


def ensure_single_instance():
    # Get the name of the current process
    current_process_name = sys.argv[0]

    c = wmi.WMI()

    # Get a list of running processes
    processes = c.Win32_Process()

    # Check if the current process is already running
    for process in processes:
        if process.Name == current_process_name and process.ProcessId != os.getpid():
            print('Another instance of the CLI is already running.')
            sys.exit(errno.ECANCELED)


def get_exec_file(file):
    if os.path.exists(f'{file}.py'):
        return f'{file}.py'

    if os.path.exists(f'{file}.cmd'):
        return f'{file}.cmd'

    if os.path.exists(f'{file}.ps1'):
        return f'{file}.ps1'

    return None


def run_script(script):
    script_file = get_exec_file(script)
    if not script_file:
        return

    cmd = []
    if script_file.endswith('.cmd'):
        cmd = ['cmd', '/c', script_file]
    elif script_file.endswith('.ps1'):
        cmd = ['powershell', '-File', script_file]
    elif script_file.endswith('.py'):
        cmd = ['python', script_file]

    if cmd:
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f'Error trying execute script: {e}')


def verify_hash(file_, expected_hash):
    with open(file_, 'rb') as f:
        hash_ = hashlib.sha256(f.read()).hexdigest()

    if hash_ != expected_hash:
        raise ValueError('Hash mismatch')


def delete_files_with_pattern(directory, pattern):
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


def create_package_info(directory, package_name):
    pms_path = os.path.join(directory, package_name, 'pms')

    shutil.copy(
        os.path.join(pms_path, PKG_METADATA_FILE),
        os.path.join(PKG_INFO_PATH, f'{package_name}.{PKG_METADATA_FILE}')
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
            for item in archives + [data_path]:
                if os.path.isfile(os.path.join(root, item)):
                    files.append(os.path.relpath(os.path.join(root, item), data_path))

        if files:
            with open(os.path.join(PKG_INFO_PATH, f'{package_name}.list'), 'w') as f:
                for item in sorted(files):
                    f.write(f"{item}\n")


def check_metadata_content(metadata):
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
            if not re.match(r'^[a-zA-Z0-9_-]+(\s*\([<>]=?\s*[0-9.]+\))?$', dependency):
                raise ValueError(f'dependency is not in the expected format: {dependency}')


def check_status_phases(desired, current):
    if desired not in STATUS_DESIRED:
        print(f'{desired} status has an incorrect value')
        sys.exit(errno.EINVAL)

    if current not in STATUS_CURRENT:
        print(f'{current} status has an incorrect value')
        sys.exit(errno.EINVAL)


def load_status():
    with open(STATUS_PATH) as f:
        return json.load(f)


def write_status(info):
    with open(STATUS_PATH, 'w') as f:
        json.dump(info, f, indent=2)


def update_package_status(name, version, desired, current, date=None):
    check_status_phases(desired, current)

    if not os.path.isfile(STATUS_PATH):
        status_info = {
            name: {
                version: {
                    'status': {
                        'desired': desired,
                        'current': current
                    }
                }
            }
        }
    else:
        status_info = load_status()
        if name in status_info:
            if version in status_info[name]:
                status_info[name][version] = {'status': {'desired': desired, 'current': current}}
            else:
                status_info[name] = {version: {'status': {'desired': desired, 'current': current}}}
        else:
            status_info[name] = {version: {'status': {'desired': desired, 'current': current}}}

    if date:
        if desired == 'i' and current == 'i':
            status_info[name][version]['install_date'] = date
        if desired == 'u' and current == 'n':
            status_info[name][version]['remove_date'] = date

    write_status(status_info)

    return status_info


def get_package_status(name):
    if not os.path.isfile(STATUS_PATH):
        return None

    status_info = load_status()
    if name in status_info:
        return status_info[name]

    return None


def get_installed_package_status(name):
    if not os.path.isfile(STATUS_PATH):
        raise ValueError(f"Status info file {STATUS_PATH} does not exist")

    status_info = load_status()
    if name in status_info:
        for version, info in status_info[name].items():
            if info['status']['desired'] == 'i' and info['status']['current'] == 'i':
                return {version: info}

        raise ValueError(f"No installed version of package {name} found")
    else:
        raise ValueError(f"Package {name} not found in status info")


def is_package_installed(name, version):
    status = get_package_status(name)
    if version in status:
        return status[version]['status']['desired'] == 'i' and status[version]['status']['current'] == 'i'

    return False


def parse_dependency(dependency):
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


def parse_version(version):
    """
    Parses a version string in condition and version

    :param version: version string
    :return: tuple with condition and version
    """
    if not version or ' ' not in version:
        return '=', None

    condition, version = version.replace('(', '').replace(')', '').split(' ', 1)

    return condition, version


def check_dependency(name, installed_version, condition, required_version):
    if condition == '=':
        if installed_version != required_version:
            raise ValueError(
                f'Dependency {name} has version {installed_version},'
                f' but version {required_version} is required.'
            )
    elif condition == '>':
        if installed_version <= required_version:
            raise ValueError(
                f'Dependency {name} has version {installed_version},'
                f' but version greater than {required_version} is required.'
            )
    elif condition == '<':
        if installed_version >= required_version:
            raise ValueError(
                f'Dependency {name} has version {installed_version},'
                f' but version less than {required_version} is required.'
            )
    elif condition == '>=':
        if installed_version < required_version:
            raise ValueError(
                f'Dependency {name} has version {installed_version},'
                f' but version greater than or equal to {required_version} is required.'
            )
    elif condition == '<=':
        if installed_version > required_version:
            raise ValueError(
                f'Dependency {name} has version {installed_version},'
                f' but version less than or equal to {required_version} is required.'
            )

    return True


def is_dependency_installed(name, condition, version, installed_packages):
    if name in installed_packages:
        if version is None:
            return True

        installed_version = packaging.version.parse(installed_packages[name])
        required_version = packaging.version.parse(version)
        return check_dependency(name, installed_version, condition, required_version)

    return False


def check_version_condition(dependency_version, condition, required_version):
    if condition == '=':
        return dependency_version == required_version
    elif condition == '>':
        return dependency_version > required_version
    elif condition == '<':
        return dependency_version < required_version
    elif condition == '>=':
        return dependency_version >= required_version
    elif condition == '<=':
        return dependency_version <= required_version
    else:  # unknown condition value
        return False
