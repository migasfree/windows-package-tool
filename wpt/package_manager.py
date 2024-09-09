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
import json
import re
import shutil
import tarfile
import hashlib
import errno
import packaging.version
import requests
try:
    import winreg
except ImportError:
    pass

from datetime import datetime

from .settings import (
    PMS, SOURCES_PATH, PKG_EXT, REPO_FILE, PKG_ARCH, PKG_INFO_PATH,
    REPO_LOCAL_PATH, PKG_METADATA_FILE, PMS_TEMP_PATH,
    STATUS_DESIRED, STATUS_CURRENT,
)
from .utils import (
    extract_tar_gz, run_script, verify_hash, delete_files_with_pattern,
    create_package_info, check_metadata_content, check_app_dirs,
    update_package_status, get_package_status, get_installed_package_status,
    is_package_installed, parse_dependency, parse_version, is_dependency_installed,
    check_version_condition, load_status,
)


class PackageManager:
    _repository_info = {}

    def __init__(self, quiet=False, assume_yes=False):
        self.quiet = quiet
        self.assume_yes = assume_yes

    def get_repository_sources(self):
        if not os.path.isfile(SOURCES_PATH):
            print(f'File with repositories lists ({SOURCES_PATH}) does not exist. Create a new one.')
            sys.exit(errno.ENOENT)

        # Read the URLs from the sources file
        with open(SOURCES_PATH) as f:
            repository_sources = [line.strip() for line in f if not line.startswith('#')]

        if not self.quiet:
            print('Package sources:')
            print("\n".join(repository_sources))
            print()

        return repository_sources

    def update_local_repo_info(self, regenerate=False):
        check_app_dirs()

        if os.path.isfile(REPO_LOCAL_PATH) and not regenerate:
            with open(REPO_LOCAL_PATH) as f:
                self._repository_info = json.load(f)

            return self._repository_info

        # Initialize an empty dictionary to store the repository info
        self._repository_info = {}

        # Iterate over the repository URLs
        for item in self.get_repository_sources():
            url, _ = item.split(' ', 1)

            if not self.quiet:
                print(f'Downloading package index from {url}')

            # Make a request to the repository's index file
            response = requests.get(f'{url}/{REPO_FILE}')
            repo_info = json.loads(response.text)

            # Add the URL to the package metadata
            for package_name, package_info in repo_info.items():
                for version, version_info in package_info.items():
                    version_info['metadata']['url'] = url

            self._repository_info.update(repo_info)

        if not self.quiet:
            print(f'Writing package list in {REPO_LOCAL_PATH}')

        # Store the repository info in a local cache
        with open(REPO_LOCAL_PATH, 'w') as f:
            json.dump(self._repository_info, f, indent=2)

        return self._repository_info

    def _get_package_metadata(self, package_name, package_version=None):
        if os.path.isfile(package_name):
            target = os.path.join(PMS_TEMP_PATH, package_name)
            shutil.copy(package_name, target)

            package_name = os.path.basename(package_name).split('_')[0]
            path = os.path.join(PMS_TEMP_PATH, package_name)
            extract_tar_gz(target, path)

            with open(os.path.join(path, 'pms', PKG_METADATA_FILE)) as f:
                return json.load(f)

        if self._repository_info:
            if package_name not in self._repository_info:
                print(f'Package {package_name} not found in repository info')
                sys.exit(errno.ENOENT)

            if not package_version:
                package_version = max(self._repository_info[package_name].keys())

            metadata = self._repository_info[package_name][package_version]['metadata']
            metadata['name'] = package_name
            metadata['version'] = package_version

            return metadata

        with open(os.path.join(PKG_INFO_PATH, f'{package_name}.{PKG_METADATA_FILE}')) as f:
            return json.load(f)

    def download_package(self, metadata):
        filename = self._repository_info[metadata['name']][metadata['version']]['filename']
        url = f"{metadata['url']}/{filename}"
        if not self.quiet:
            print(f'Downloading package from {url}')
        try:
            response = requests.get(url, stream=True)
        except requests.ConnectionError as e:
            print(e)
            sys.exit(errno.ECONNREFUSED)

        target = os.path.join(PMS_TEMP_PATH, f'{metadata["name"]}_{metadata["version"]}_{PKG_ARCH}{PKG_EXT}')
        with open(target, 'wb') as f:
            shutil.copyfileobj(response.raw, f)

        if not self.quiet:
            print(f'Package downloaded in {target}')

        expected_hash = self._repository_info[metadata['name']][metadata['version']]['hash']
        try:
            verify_hash(target, expected_hash)
        except ValueError as e:
            print(e)
            sys.exit(errno.EINVAL)

        if not self.quiet:
            print('Package verified')

        return target

    def add_package_metadata_to_registry(self, metadata):
        with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, f'SOFTWARE\\{PMS}\\Packages') as key:
            with winreg.CreateKey(key, metadata['name']) as subkey:
                winreg.SetValueEx(subkey, 'Name', 0, winreg.REG_SZ, metadata['name'])
                winreg.SetValueEx(subkey, 'Version', 0, winreg.REG_SZ, metadata['version'])
                winreg.SetValueEx(subkey, 'Description', 0, winreg.REG_SZ, metadata['description'])
                winreg.SetValueEx(subkey, 'Maintainer', 0, winreg.REG_SZ, metadata['maintainer'])
                winreg.SetValueEx(subkey, 'Specification', 0, winreg.REG_SZ, metadata['specification'])

                if 'homepage' in metadata:
                    winreg.SetValueEx(subkey, 'Homepage', 0, winreg.REG_SZ, metadata['homepage'])

                if 'dependencies' in metadata:
                    winreg.SetValueEx(subkey, 'Dependencies', 0, winreg.REG_SZ, ', '.join(metadata['dependencies']))

                winreg.SetValueEx(subkey, 'InstallDate', 0, winreg.REG_SZ, datetime.now().isoformat())

    def configure_package(self, metadata):
        if not self.quiet:
            print(f'Configuring package {metadata["name"]}...')

        create_package_info(PMS_TEMP_PATH, metadata['name'])

        pms_path = os.path.join(PMS_TEMP_PATH, metadata['name'], 'pms')

        update_package_status(metadata['name'], metadata['version'], desired='i', current='h')

        try:
            run_script(os.path.join(pms_path, 'preinst'))
            run_script(os.path.join(pms_path, 'install'))
            run_script(os.path.join(pms_path, 'postinst'))
        except RuntimeError as e:
            print(e)
            sys.exit(errno.ECANCELED)

        self.add_package_metadata_to_registry(metadata)

        update_package_status(
            metadata['name'], metadata['version'],
            desired='i', current='i', date=datetime.now().isoformat()
        )

        if not self.quiet:
            print(f'Package {metadata["name"]}_{metadata["version"]} installed succesfully')

    def install_dependencies(self, packages):
        if not packages:
            return

        # only install not installed packages
        packages_to_install = packages.copy()
        for package_name, package_version in packages_to_install.items():
            if is_package_installed(package_name, package_version):
                del packages[package_name]

        if not self.assume_yes and packages:
            print("The following packages will also be installed:")
            for name, version in packages.items():
                print(name, version)
            confirm = input("Are you sure you want to continue? (Y/n): ")
            if confirm.lower() == 'n':
                print("Operation cancelled.")
                sys.exit(errno.ECANCELED)

        for package_name, package_version in packages.items():
            self.install_package(package_name, package_version)

    def install_package(self, package_name, package_version=None):
        if not self.quiet:
            print(
                f'Installing package {package_name}',
                f', version: {package_version}' if package_version else '',
                '...'
            )

        if not self._repository_info:
            self.update_local_repo_info()

        installed_packages = {item['name']: item['version'] for item in self.get_installed_packages()}

        package_metadata = self._get_package_metadata(package_name, package_version)
        update_package_status(package_metadata['name'], package_metadata['version'], desired='i', current='n')

        if os.path.isfile(package_name):
            target = os.path.join(PMS_TEMP_PATH, package_name)
        else:
            target = self.download_package(package_metadata)

        path = os.path.join(PMS_TEMP_PATH, package_metadata['name'])

        extract_tar_gz(target, path)

        update_package_status(package_metadata['name'], package_metadata['version'], desired='i', current='u')

        try:
            packages_to_install = self.resolve_dependencies(
                package_metadata['name'],
                package_metadata['version'],
                installed_packages
            )
            del packages_to_install[package_metadata['name']]
        except ValueError as e:
            print(e)
            sys.exit(errno.EPERM)

        self.install_dependencies(packages_to_install)

        self.configure_package(package_metadata)

        # clean temporary files
        shutil.rmtree(path)
        os.remove(target)

    def remove_dependencies(self, packages):
        if not packages:
            return

        # only remove installed packages
        packages_to_remove = packages.copy()
        for package_name, package_version in packages_to_remove.items():
            if not is_package_installed(package_name, package_version):
                del packages[package_name]

        if not self.assume_yes and packages:
            print("The following packages will also be removed:")
            for name, version in packages.items():
                print(name, version)
            confirm = input("Are you sure you want to continue? (y/N): ")
            if confirm.lower() != 'y':
                print("Operation cancelled.")
                sys.exit(errno.ECANCELED)

        for package_name, package_version in packages.items():
            self.remove_package(package_name, force=True)

    def remove_package_metadata_from_registry(self, package_name):
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f'SOFTWARE\\{PMS}\\Packages', 0, winreg.KEY_ALL_ACCESS) as key:
            winreg.DeleteKey(key, package_name)

    def deconfigure_package(self, metadata):
        if not self.quiet:
            print(f"Removing package {metadata['name']}_{metadata['version']}...")

        update_package_status(metadata['name'], metadata['version'], desired='r', current='i')
        self.remove_package_metadata_from_registry(metadata['name'])
        update_package_status(metadata['name'], metadata['version'], desired='r', current='h')

        path = os.path.join(PKG_INFO_PATH, metadata['name'])

        try:
            run_script(f'{path}.prerm')
            run_script(f'{path}.remove')
            run_script(f'{path}.postrm')
        except RuntimeError as e:
            print(e)
            sys.exit(errno.ECANCELED)

        # Remove the package files
        delete_files_with_pattern(PKG_INFO_PATH, metadata['name'])
        update_package_status(
            metadata['name'], metadata['version'],
            desired='u', current='n', date=datetime.now().isoformat()
        )

        if not self.quiet:
            print(f"Package {metadata['name']}_{metadata['version']} removed successfully")

    def remove_package(self, package_name, force=False):
        try:
            status = get_installed_package_status(package_name)
            package_version = list(status.keys())[0]
        except ValueError as e:
            print(e)
            sys.exit(errno.ENODATA)

        self.update_local_repo_info()
        package_metadata = self._repository_info[package_name][package_version]['metadata']

        if not force:
            # Check for unmet dependencies
            installed_packages = {item['name']: item['version'] for item in self.get_installed_packages()}
            try:
                packages_to_remove = self.resolve_dependencies(
                    package_name,
                    package_version,
                    installed_packages,
                )
                del packages_to_remove[package_name]
            except ValueError as e:
                print(f'Cannot remove package {package_name} due to unmet dependencies: {e}')
                sys.exit(errno.EPERM)

            self.remove_dependencies(packages_to_remove)

        self.deconfigure_package(package_metadata)

    def get_installed_software(self):
        software = []

        # Query the Windows registry for installed software
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall') as key:
            for i in range(winreg.QueryInfoKey(key)[0]):
                subkey_name = winreg.EnumKey(key, i)
                with winreg.OpenKey(key, subkey_name) as subkey:
                    try:
                        name = winreg.QueryValueEx(subkey, 'DisplayName')[0]
                    except FileNotFoundError:
                        continue

                    try:
                        version = winreg.QueryValueEx(subkey, 'DisplayVersion')[0]
                    except FileNotFoundError:
                        version = '0.0.0'

                    try:
                        publisher = winreg.QueryValueEx(subkey, 'Publisher')[0]
                    except FileNotFoundError:
                        publisher = ''

                    try:
                        description = winreg.QueryValueEx(subkey, 'Comments')[0]
                    except FileNotFoundError:
                        description = ''

                software.append({
                    'name': name,
                    'version': version,
                    'description': description,
                    'publisher': publisher
                })

        return software + self.get_pms_installed_software()

    def get_pms_installed_software(self):
        software = []

        try:
            # Query the Windows registry for packages managed by WPT
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f'SOFTWARE\\{PMS}\\Packages') as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    subkey_name = winreg.EnumKey(key, i)
                    with winreg.OpenKey(key, subkey_name) as subkey:
                        try:
                            name = winreg.QueryValueEx(subkey, 'Name')[0]
                        except FileNotFoundError:
                            name = subkey_name

                        try:
                            version = winreg.QueryValueEx(subkey, 'Version')[0]
                        except FileNotFoundError:
                            version = '0.0.0'

                        try:
                            description = winreg.QueryValueEx(subkey, 'Description')[0]
                        except FileNotFoundError:
                            description = 'No description available'

                        try:
                            maintainer = winreg.QueryValueEx(subkey, 'Maintainer')[0]
                        except FileNotFoundError:
                            maintainer = 'Unknown'

                        try:
                            specification = winreg.QueryValueEx(subkey, 'Specification')[0]
                        except FileNotFoundError:
                            specification = '1.0.0'

                        try:
                            homepage = winreg.QueryValueEx(subkey, 'Homepage')[0]
                        except FileNotFoundError:
                            homepage = 'No homepage available'

                        software.append({
                            'name': name,
                            'version': version,
                            'description': description,
                            'maintainer': maintainer,
                            'specification': specification,
                            'homepage': homepage
                        })
        except FileNotFoundError:
            pass

        return software

    def get_installed_packages(self):
        status_info = load_status()
        installed_packages = {
            package: version for package, versions in status_info.items()
            for version, info in versions.items()
            if info['status']['desired'] == 'i' and info['status']['current'] == 'i'
        }

        if not self._repository_info:
            self.update_local_repo_info()

        return [
            self._repository_info[package][version]['metadata']
            for package, version in installed_packages.items()
        ]

    def list_installed_packages(self, all_=False, summary=False):
        if all_:
            packages = self.get_installed_software()
        else:
            packages = self.get_pms_installed_software()

        if not packages:
            print('No packages found')
            sys.exit(errno.ENODATA)

        for pkg in packages:
            if summary:
                print(f"{pkg['name']}_{pkg['version']}_{PKG_ARCH}")
            else:
                if pkg['description']:
                    print(f"{pkg['name']} ({pkg['version']}) - {pkg['description']}")
                else:
                    print(f"{pkg['name']} ({pkg['version']})")

    def search_packages(self, query=None, summary=False):
        if not self._repository_info:
            self.update_local_repo_info()

        if not query or query == '*':
            pattern = re.compile('.*')
        else:
            pattern = re.compile(query.lower())

        ret = set()
        for package_name, package_info in self._repository_info.items():
            latest_version = max(package_info.keys())

            package_metadata = self._repository_info[package_name][latest_version]['metadata']

            # Check if the query matches the package name or description
            if pattern.search(package_name.lower()) or pattern.search(package_metadata['description'].lower()):
                if summary:
                    ret.add(package_name)
                else:
                    ret.add(f"{package_name} {latest_version} - {package_metadata['description']}")

        for item in sorted(ret):
            print(item)

    def _get_latest_dependency_version(self, name, version, condition):
        if version is None:
            return max(self._repository_info[name].keys(), key=packaging.version.parse)

        required_version = packaging.version.parse(version)
        for version, metadata in self._repository_info[name].items():
            dependency_version = packaging.version.parse(version)
            if check_version_condition(dependency_version, condition, required_version):
                return version

        raise ValueError(f'Dependency {name} is not available in the package repository.')

    def resolve_dependencies(
        self, package_name, package_version,
        installed_packages=None,
        processed_packages=None,
    ):
        """
        Resolves package dependencies

        Args:
            package_name (str)
            package_version (str)
            installed_packages (dict): ({name1: version1, name2: version2, ...})
            processed_packages (dict)

        Raises:
            ValueError: if circular dependency is detected
        """
        if installed_packages is None:
            installed_packages = {}

        package_metadata = self._get_package_metadata(package_name, package_version)

        if processed_packages is None:
            processed_packages = {}

        if package_name in processed_packages:
            raise ValueError(f"Circular dependency detected: {package_name}")

        processed_packages[package_name] = package_version

        dependencies = package_metadata.get('dependencies', [])

        for dependency in dependencies:
            dependency_name, dependency_version = parse_dependency(dependency)
            condition, version = parse_version(dependency_version)

            if is_dependency_installed(dependency_name, condition, version, installed_packages):
                continue

            dependency_version = self._get_latest_dependency_version(dependency_name, version, condition)

            # Recursively resolve the dependencies
            self.resolve_dependencies(
                dependency_name, str(dependency_version),
                installed_packages,
                processed_packages,
            )

        installed_packages.update(processed_packages)
        return installed_packages

    def upgrade(self, installed_packages=None):
        if not installed_packages:
            installed_packages = self.get_installed_packages()

        if not self._repository_info:
            self.update_local_repo_info()

        for package in installed_packages:
            # Check if the package is available in the package repository
            if package['name'] in self._repository_info:
                # Find the latest version of the package that is available in the package repository
                latest_version = max(
                    self._repository_info[package['name']].keys(),
                    key=packaging.version.parse
                )

                # Check if the latest version is newer than the installed version
                if packaging.version.parse(latest_version) > packaging.version.parse(package['version']):
                    self.remove_package(package['name'], force=True)
                    self.install_package(package['name'])

                    # Update the installed packages dictionary
                    installed_packages[package['name']] = latest_version

        return installed_packages

    def show_status(self, package_name, status):
        self.update_local_repo_info()
        version = list(status.keys())[0]

        if version in self._repository_info[package_name]:
            metadata = self._repository_info[package_name][version]
            for key, value in metadata.items():
                if key == 'metadata':
                    for k, v in value.items():
                        print(f'{k.capitalize()}: {v}')
                else:
                    print(f'{key.capitalize()}: {value}')

        print(
            f"Desired Status: ({status[version]['status']['desired']})"
            f" {STATUS_DESIRED[status[version]['status']['desired']]}"
        )
        print(
            f"Current Status: ({status[version]['status']['current']})"
            f" {STATUS_CURRENT[status[version]['status']['current']]}"
        )

        if 'install_date' in status[version]:
            print(f"Install Date: {status[version]['install_date']}")

        if 'remove_date' in status[version]:
            print(f"Remove Date: {status[version]['remove_date']}")

    def status(self, package_name, is_installed=None):
        try:
            status = get_installed_package_status(package_name)
            if is_installed:
                sys.exit()
        except ValueError:
            if is_installed:
                sys.exit(errno.ENODATA)

            status = get_package_status(package_name)
            if not status:
                print(f'{package_name} has never been installed or removed on the system')
                sys.exit(errno.ENODATA)

        self.show_status(package_name, status)

    def clean(self):
        shutil.rmtree(PMS_TEMP_PATH)
        os.makedirs(PMS_TEMP_PATH)
        if not self.quiet:
            print(f'Temporal path cleaned: {PMS_TEMP_PATH}')
        if os.path.isfile(REPO_LOCAL_PATH):
            os.remove(REPO_LOCAL_PATH)
            if not self.quiet:
                print(f'File {REPO_LOCAL_PATH} removed')

    def build(self, package_directory):
        pms_directory = os.path.join(package_directory, 'pms')
        if not os.path.isdir(pms_directory):
            raise ValueError('pms directory does not exist')

        metadata_file = os.path.join(pms_directory, PKG_METADATA_FILE)
        if not os.path.isfile(metadata_file):
            raise ValueError(f'{metadata_file} file does not exist')

        with open(metadata_file) as f:
            metadata = json.load(f)

        check_metadata_content(metadata)

        data_directory = os.path.join(package_directory, 'data')
        if os.path.isdir(data_directory):
            install_file = None
            remove_file = None
            for ext in ['.ps1', '.cmd', '.py']:
                if os.path.isfile(os.path.join(pms_directory, f'install{ext}')):
                    install_file = f'install{ext}'
                if os.path.isfile(os.path.join(pms_directory, f'remove{ext}')):
                    remove_file = f'remove{ext}'
            if install_file is None or remove_file is None:
                raise ValueError('install and/or remove file with expected extension not found in pms directory')

        package_file = f"{metadata['name']}_{metadata['version']}_{PKG_ARCH}{PKG_EXT}"
        if os.path.isfile(package_file):
            os.remove(package_file)

        # Create a tar.gz file of the package directory
        os.chdir(package_directory)
        with tarfile.open(package_file, 'w:gz') as tar:
            for file in os.listdir('.'):
                tar.add(file)

        shutil.move(package_file, '..')
        os.chdir('..')

        with open(package_file, 'rb') as f:
            hash_ = hashlib.sha256(f.read()).hexdigest()

        print(f'Created package file: {package_file}')
        print(f'Hash of package file: {hash_}')

        return package_file, hash_
