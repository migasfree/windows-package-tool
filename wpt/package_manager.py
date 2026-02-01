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

import contextlib
import errno
import hashlib
import json
import os
import re
import shutil
import sys
import tarfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import packaging.version
import requests
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.prompt import Confirm
from rich.table import Table

with contextlib.suppress(ImportError):
    import winreg

from .logging import logger
from .settings import (
    PKG_ARCH,
    PKG_EXT,
    PKG_INFO_PATH,
    PKG_METADATA_FILE,
    PMS,
    PMS_TEMP_PATH,
    REPO_FILE,
    REPO_LOCAL_PATH,
    SOURCES_PATH,
    STATUS_CURRENT,
    STATUS_DESIRED,
    THEME,
)
from .utils import (
    check_app_dirs,
    check_metadata_content,
    check_version_condition,
    create_package_info,
    delete_files_with_pattern,
    extract_tar_gz,
    get_installed_package_status,
    get_package_status,
    is_dependency_installed,
    is_package_installed,
    load_status,
    parse_dependency,
    parse_version,
    run_script,
    update_package_status,
    verify_hash,
)


def _get_registry_value(key, name: str, default: Any = None) -> Any:
    """Get a value from a Windows registry key.

    Args:
        key: Open registry key handle
        name: Name of the value to retrieve
        default: Default value if not found

    Returns:
        The registry value or default if not found
    """
    try:
        return winreg.QueryValueEx(key, name)[0]
    except FileNotFoundError:
        return default


class PackageManager:
    _repository_info: Dict[str, Any] = {}  # noqa: RUF012

    def __init__(
        self,
        quiet: bool = False,
        assume_yes: bool = False,
        verify: Any = None,
    ) -> None:
        self.quiet = quiet
        self.assume_yes = assume_yes

        if verify is None:
            from .config import get_config

            self.verify = get_config().ssl_verify
        else:
            self.verify = verify

        self.console = Console(quiet=self.quiet, theme=THEME)

    def get_repository_sources(self) -> List[str]:
        if not os.path.isfile(SOURCES_PATH):
            raise FileNotFoundError(f'File with repositories lists ({SOURCES_PATH}) does not exist. Create a new one.')

        # Read the URLs from the sources file
        with open(SOURCES_PATH) as f:
            repository_sources = [line.strip() for line in f if not line.startswith('#')]

        if not self.quiet:
            self.console.print('[bold]Package sources:[/bold]')
            self.console.print('\n'.join(repository_sources))
            self.console.print()

        return repository_sources

    def update_local_repo_info(self, regenerate: bool = False) -> Dict[str, Any]:
        check_app_dirs()

        if os.path.isfile(REPO_LOCAL_PATH) and not regenerate:
            with open(REPO_LOCAL_PATH) as f:
                self._repository_info = json.load(f)

            return self._repository_info

        # Initialize an empty dictionary to store the repository info
        self._repository_info = {}

        logger.debug('Updating local repository info from %d sources', len(self.get_repository_sources()))

        with self.console.status('[success]Updating repository information...[/success]', spinner='dots'):
            # Iterate over the repository URLs
            for item in self.get_repository_sources():
                url, _ = item.split(' ', 1)

                if not self.quiet:
                    self.console.print(f'Downloading package index from [url]{url}[/url]')

                if url.startswith('http://'):
                    logger.warning('Using insecure repository: %s', url)

                # Make a request to the repository's index file
                response = requests.get(f'{url}/{REPO_FILE}', verify=self.verify)

                try:
                    repo_info = json.loads(response.text)
                except json.JSONDecodeError as e:
                    logger.error('Failed to decode JSON from %s (Status: %d)', url, response.status_code)
                    logger.debug('Response content:\n%s', response.text)
                    if not self.quiet:
                        self.console.print(f'[error]Error decoding repository data from {url}: {e}[/error]')
                    continue

                # Add the URL to the package metadata
                for _package_name, package_info in repo_info.items():
                    for _version, version_info in package_info.items():
                        version_info['metadata']['url'] = url

                self._repository_info.update(repo_info)

        logger.debug('Local repository info updated with %d packages', len(self._repository_info))

        if not self.quiet:
            self.console.print(f'Writing package list in [bold]{REPO_LOCAL_PATH}[/bold]')

        # Store the repository info in a local cache
        with open(REPO_LOCAL_PATH, 'w') as f:
            json.dump(self._repository_info, f, indent=2)

        return self._repository_info

    def _get_package_metadata(self, package_name: str, package_version: Optional[str] = None) -> Dict[str, Any]:
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
                raise KeyError(f'Package {package_name} not found in repository info')

            if not package_version:
                package_version = max(self._repository_info[package_name].keys())

            metadata = self._repository_info[package_name][package_version]['metadata']
            metadata['name'] = package_name
            metadata['version'] = package_version

            return metadata

        with open(os.path.join(PKG_INFO_PATH, f'{package_name}.{PKG_METADATA_FILE}')) as f:
            return json.load(f)

    def download_package(self, metadata: Dict[str, Any]) -> str:
        filename = self._repository_info[metadata['name']][metadata['version']]['filename']
        url = f'{metadata["url"]}/{filename}'
        logger.info('Downloading package from %s', url)
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn('[info]{task.description}'),
                BarColumn(),
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
                console=self.console,
                transient=True,
                disable=self.quiet,
            ) as progress:
                task = progress.add_task(f'Downloading {filename}', total=None)
                response = requests.get(url, stream=True, verify=self.verify)
                total_length = response.headers.get('content-length')

                if total_length:
                    progress.update(task, total=int(total_length))

                target = os.path.join(PMS_TEMP_PATH, f'{metadata["name"]}_{metadata["version"]}_{PKG_ARCH}{PKG_EXT}')
                with open(target, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            progress.update(task, advance=len(chunk))
        except requests.ConnectionError as e:
            raise RuntimeError(f'Connection error downloading package: {e}') from e

        logger.debug('Package downloaded to %s', target)

        expected_hash = self._repository_info[metadata['name']][metadata['version']]['hash']
        try:
            verify_hash(target, expected_hash)
        except ValueError as e:
            raise ValueError(f'Package verification failed: {e}') from e

        logger.debug('Package hash verified')

        return target

    def add_package_metadata_to_registry(self, metadata: Dict[str, Any]) -> None:
        with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, f'SOFTWARE\\{PMS}\\Packages') as key:  # noqa: SIM117
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

    def configure_package(self, metadata: Dict[str, Any]) -> None:
        logger.info('Configuring package %s...', metadata['name'])

        create_package_info(PMS_TEMP_PATH, metadata['name'])

        pms_path = os.path.join(PMS_TEMP_PATH, metadata['name'], 'pms')

        update_package_status(metadata['name'], metadata['version'], desired='i', current='h')

        try:
            run_script(os.path.join(pms_path, 'preinst'))
            run_script(os.path.join(pms_path, 'install'))
            run_script(os.path.join(pms_path, 'postinst'))
        except RuntimeError as e:
            raise RuntimeError(f'Package configuration failed: {e}') from e

        self.add_package_metadata_to_registry(metadata)

        update_package_status(
            metadata['name'], metadata['version'], desired='i', current='i', date=datetime.now().isoformat()
        )

        logger.info('Package %s_%s installed successfully', metadata['name'], metadata['version'])

    def install_dependencies(self, packages: Dict[str, str]) -> None:
        if not packages:
            return

        # Filter to only packages that need installation
        packages = {name: version for name, version in packages.items() if not is_package_installed(name, version)}

        if not packages:
            return

        if not self.assume_yes and packages:
            self.console.print('[warning]The following packages will also be installed:[/warning]')
            for name, version in packages.items():
                self.console.print(f' - {name} ({version})')

            if not Confirm.ask('Are you sure you want to continue?', default=True, console=self.console):
                raise RuntimeError('Operation cancelled by user.')

        for package_name, package_version in packages.items():
            self.install_package(package_name, package_version)

    def install_package(self, package_name: str, package_version: Optional[str] = None) -> bool:
        logger.debug('Starting installation of package %s (version=%s)', package_name, package_version)
        if not self.quiet:
            self.console.print(
                f'Installing package [bold]{package_name}[/bold]',
                f', version: {package_version}' if package_version else '',
                '...',
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
            logger.debug('Resolving dependencies for %s', package_metadata['name'])
            packages_to_install = self.resolve_dependencies(
                package_metadata['name'], package_metadata['version'], installed_packages
            )
            del packages_to_install[package_metadata['name']]
        except ValueError as e:
            raise ValueError(f'Dependency resolution failed: {e}') from e

        self.install_dependencies(packages_to_install)

        self.configure_package(package_metadata)

        # clean temporary files
        shutil.rmtree(path)
        os.remove(target)

    def remove_dependencies(self, packages: Dict[str, str]) -> None:
        if not packages:
            return

        # Filter to only installed packages
        packages = {name: version for name, version in packages.items() if is_package_installed(name, version)}

        if not packages:
            return

        if not self.assume_yes and packages:
            self.console.print('[warning]The following packages will also be removed:[/warning]')
            for name, version in packages.items():
                self.console.print(f' - {name} ({version})')

            if not Confirm.ask('Are you sure you want to continue?', default=True, console=self.console):
                raise RuntimeError('Operation cancelled by user.')

        for package_name in packages:
            self.remove_package(package_name, force=True)

    def remove_package_metadata_from_registry(self, package_name: str) -> None:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f'SOFTWARE\\{PMS}\\Packages', 0, winreg.KEY_ALL_ACCESS) as key:
            winreg.DeleteKey(key, package_name)

    def deconfigure_package(self, metadata: Dict[str, Any]) -> None:
        logger.info('Removing package %s_%s...', metadata['name'], metadata['version'])

        update_package_status(metadata['name'], metadata['version'], desired='r', current='i')
        self.remove_package_metadata_from_registry(metadata['name'])
        update_package_status(metadata['name'], metadata['version'], desired='r', current='h')

        path = os.path.join(PKG_INFO_PATH, metadata['name'])

        try:
            run_script(f'{path}.prerm')
            run_script(f'{path}.remove')
            run_script(f'{path}.postrm')
        except RuntimeError as e:
            raise RuntimeError(f'Package deconfiguration failed: {e}') from e

        # Remove the package files
        delete_files_with_pattern(PKG_INFO_PATH, metadata['name'])
        update_package_status(
            metadata['name'], metadata['version'], desired='u', current='n', date=datetime.now().isoformat()
        )

        logger.info('Package %s_%s removed successfully', metadata['name'], metadata['version'])

    def remove_package(self, package_name: str, force: bool = False) -> None:
        logger.debug('Starting removal of package %s (force=%s)', package_name, force)
        try:
            status = get_installed_package_status(package_name)
            package_version = next(iter(status.keys()))
        except ValueError as e:
            raise ValueError(f'Package not found or not installed: {package_name}') from e

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
                raise ValueError(f'Cannot remove package {package_name} due to unmet dependencies: {e}') from e

            self.remove_dependencies(packages_to_remove)

        self.deconfigure_package(package_metadata)

    def get_installed_software(self) -> List[Dict[str, Any]]:
        software = []

        # Query the Windows registry for installed software
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall') as key:
            for i in range(winreg.QueryInfoKey(key)[0]):
                subkey_name = winreg.EnumKey(key, i)
                with winreg.OpenKey(key, subkey_name) as subkey:
                    name = _get_registry_value(subkey, 'DisplayName')
                    if name is None:
                        continue

                    software.append(
                        {
                            'name': name,
                            'version': _get_registry_value(subkey, 'DisplayVersion', '0.0.0'),
                            'description': _get_registry_value(subkey, 'Comments', ''),
                            'publisher': _get_registry_value(subkey, 'Publisher', ''),
                        }
                    )

        return software + self.get_pms_installed_software()

    def get_pms_installed_software(self) -> List[Dict[str, Any]]:
        software = []

        try:
            # Query the Windows registry for packages managed by WPT
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f'SOFTWARE\\{PMS}\\Packages') as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    subkey_name = winreg.EnumKey(key, i)
                    with winreg.OpenKey(key, subkey_name) as subkey:
                        software.append(
                            {
                                'name': _get_registry_value(subkey, 'Name', subkey_name),
                                'version': _get_registry_value(subkey, 'Version', '0.0.0'),
                                'description': _get_registry_value(subkey, 'Description', 'No description available'),
                                'maintainer': _get_registry_value(subkey, 'Maintainer', 'Unknown'),
                                'specification': _get_registry_value(subkey, 'Specification', '1.0.0'),
                                'homepage': _get_registry_value(subkey, 'Homepage', 'No homepage available'),
                            }
                        )
        except FileNotFoundError:
            pass

        return software

    def get_installed_packages(self) -> List[Dict[str, Any]]:
        status_info = load_status()
        installed_packages = {
            package: version
            for package, versions in status_info.items()
            for version, info in versions.items()
            if info['status']['desired'] == 'i' and info['status']['current'] == 'i'
        }

        if not self._repository_info:
            self.update_local_repo_info()

        return [self._repository_info[package][version]['metadata'] for package, version in installed_packages.items()]

    def list_installed_packages(self, all_: bool = False, summary: bool = False) -> None:
        packages = self.get_installed_software() if all_ else self.get_pms_installed_software()

        if not packages:
            raise ValueError('No packages found')

        if summary:
            for pkg in packages:
                self.console.print(f'{pkg["name"]}_{pkg["version"]}_{PKG_ARCH}')
        else:
            table = Table(show_header=True, header_style='header', box=None)
            table.add_column('Name', style='pkg.name')
            table.add_column('Version', style='pkg.version')
            table.add_column('Description')

            for pkg in packages:
                table.add_row(pkg['name'], pkg['version'], pkg['description'] or '')

            self.console.print(table)

    def search_packages(self, query: Optional[str] = None, summary: bool = False) -> None:
        if not self._repository_info:
            self.update_local_repo_info()

        pattern = re.compile('.*') if not query or query == '*' else re.compile(query.lower())

        ret = set()
        for package_name, package_info in self._repository_info.items():
            latest_version = max(package_info.keys())

            package_metadata = self._repository_info[package_name][latest_version]['metadata']

            # Check if the query matches the package name or description
            if pattern.search(package_name.lower()) or pattern.search(package_metadata['description'].lower()):
                if summary:
                    ret.add(package_name)
                else:
                    ret.add((package_name, latest_version, package_metadata['description']))

        if summary:
            for item in sorted(ret):
                self.console.print(item)
        elif ret:
            table = Table(show_header=True, header_style='header', box=None)
            table.add_column('Name', style='pkg.name')
            table.add_column('Version', style='pkg.version')
            table.add_column('Description')

            for name, version, description in sorted(ret, key=lambda x: x[0]):
                table.add_row(name, version, description)

            self.console.print(table)

    def _get_latest_dependency_version(self, name: str, version: Optional[str], condition: str) -> str:
        if version is None:
            return max(self._repository_info[name].keys(), key=packaging.version.parse)

        required_version = packaging.version.parse(version)
        for version, _metadata in self._repository_info[name].items():
            dependency_version = packaging.version.parse(version)
            if check_version_condition(dependency_version, condition, required_version):
                return version

        raise ValueError(f'Dependency {name} is not available in the package repository.')

    def resolve_dependencies(
        self,
        package_name: str,
        package_version: str,
        installed_packages: Optional[Dict[str, str]] = None,
        processed_packages: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
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
            raise ValueError(f'Circular dependency detected: {package_name}')

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
                dependency_name,
                str(dependency_version),
                installed_packages,
                processed_packages,
            )

        installed_packages.update(processed_packages)
        return installed_packages

    def upgrade(self, installed_packages: Optional[List[Dict[str, Any]]] = None) -> Dict[str, str]:
        if installed_packages is None:
            installed_packages = self.get_installed_packages()

        if not self._repository_info:
            self.update_local_repo_info()

        upgraded = {}
        for package in installed_packages:
            # Check if the package is available in the package repository
            if package['name'] in self._repository_info:
                # Find the latest version of the package that is available in the package repository
                latest_version = max(self._repository_info[package['name']].keys(), key=packaging.version.parse)

                # Check if the latest version is newer than the installed version
                if packaging.version.parse(latest_version) > packaging.version.parse(package['version']):
                    self.remove_package(package['name'], force=True)
                    self.install_package(package['name'])

                    # Add to upgraded dictionary
                    upgraded[package['name']] = latest_version

        return upgraded

    def show_status(self, package_name: str, status: Dict[str, Any]) -> None:
        self.update_local_repo_info()
        version = next(iter(status.keys()))

        try:
            metadata = self._get_package_metadata(package_name, version)
            for key, value in metadata.items():
                if key == 'metadata':
                    # Skip nested metadata if present, or flatten it
                    continue
                print(f'{key.capitalize()}: {value}')
        except (KeyError, FileNotFoundError, json.JSONDecodeError):
            # Fallback if metadata unavailable
            print(f'Name: {package_name}')
            print(f'Version: {version}')

        self.console.print(
            f'Desired Status: [bold]({status[version]["status"]["desired"]})[/bold]'
            f' {STATUS_DESIRED[status[version]["status"]["desired"]]}'
        )
        self.console.print(
            f'Current Status: [bold]({status[version]["status"]["current"]})[/bold]'
            f' {STATUS_CURRENT[status[version]["status"]["current"]]}'
        )

        if 'install_date' in status[version]:
            print(f'Install Date: {status[version]["install_date"]}')

        if 'remove_date' in status[version]:
            print(f'Remove Date: {status[version]["remove_date"]}')

    def status(self, package_name: str, is_installed: Optional[bool] = None) -> None:
        try:
            status = get_installed_package_status(package_name)
            if is_installed:
                sys.exit()
        except ValueError:
            if is_installed:
                sys.exit(errno.ENODATA)

            status = get_package_status(package_name)
            if not status:
                self.console.print(f'[yellow]{package_name} has never been installed or removed on the system[/yellow]')
                sys.exit(errno.ENODATA)

        self.show_status(package_name, status)

    def clean(self) -> None:
        shutil.rmtree(PMS_TEMP_PATH)
        os.makedirs(PMS_TEMP_PATH)
        if not self.quiet:
            self.console.print(f'Temporal path cleaned: [bold]{PMS_TEMP_PATH}[/bold]')
        if os.path.isfile(REPO_LOCAL_PATH):
            os.remove(REPO_LOCAL_PATH)
            if not self.quiet:
                self.console.print(f'File [bold]{REPO_LOCAL_PATH}[/bold] removed')

    def build(self, package_directory: str) -> Tuple[str, str]:
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

        package_file = f'{metadata["name"]}_{metadata["version"]}_{PKG_ARCH}{PKG_EXT}'
        if os.path.isfile(package_file):
            os.remove(package_file)

        # Create a tar.gz file of the package directory
        # Use try/finally to ensure we always return to original directory
        original_dir = os.getcwd()
        try:
            os.chdir(package_directory)
            with tarfile.open(package_file, 'w:gz') as tar:
                for file in os.listdir('.'):
                    tar.add(file)
            shutil.move(package_file, '..')
        finally:
            os.chdir(original_dir)

        with open(package_file, 'rb') as f:
            hash_ = hashlib.sha256(f.read()).hexdigest()

        print(f'Created package file: {package_file}')
        print(f'Hash of package file: {hash_}')

        return package_file, hash_
