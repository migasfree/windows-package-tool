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

"""Query operations mixin for PackageManager."""

import contextlib
import errno
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

import packaging.version
from rich.table import Table

with contextlib.suppress(ImportError):
    import winreg

from ..logging import logger
from ..settings import (
    PKG_ARCH,
    PKG_INFO_PATH,
    PMS,
    STATUS_CURRENT,
    STATUS_DESIRED,
)
from ..utils import (
    get_installed_package_status,
    get_package_status,
    load_status,
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


class QueryMixin:
    """Mixin class for query operations.

    Cross-mixin dependencies:
        - RepositoryMixin: update_local_repo_info(), _get_package_metadata(),
          _repository_info
    """

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

        packages = []
        for package, version in installed_packages.items():
            if package in self._repository_info and version in self._repository_info[package]:
                packages.append(self._repository_info[package][version]['metadata'])
            else:
                meta = status_info[package][version].get('metadata', {})
                if not meta:
                    meta = {
                        'name': package,
                        'version': version,
                        'summary': f'Installed package: {package}',
                        'dependencies': [],
                    }
                packages.append(meta)
        return packages

    def list_installed_packages(self, all_: bool = False, summary: bool = False) -> None:
        logger.debug('Listing installed packages (all=%s, summary=%s)', all_, summary)
        packages = self.get_installed_software() if all_ else self.get_pms_installed_software()

        if not packages:
            raise ValueError('No packages found')

        if summary:
            for pkg in packages:
                self.console.print(f'{pkg["name"]}_{pkg["version"]}_{PKG_ARCH}')
        else:
            table = Table(show_header=True, header_style='header', box=None)
            table.add_column('Status')
            table.add_column('Name', style='pkg.name')
            table.add_column('Version', style='pkg.version')
            table.add_column('Description')

            status_info = load_status()
            for pkg in packages:
                pkg_status = status_info.get(pkg['name'], {}).get(pkg['version'], {}).get('status', {})
                if pkg_status:
                    desired = pkg_status.get('desired', 'u')
                    current = pkg_status.get('current', 'n')
                    status_str = f'{desired}{current}'
                else:
                    if pkg['name'] in status_info and status_info[pkg['name']]:
                        first_ver = next(iter(status_info[pkg['name']].keys()))
                        first_status = status_info[pkg['name']][first_ver].get('status', {})
                        desired = first_status.get('desired', 'u')
                        current = first_status.get('current', 'n')
                        status_str = f'{desired}{current}'
                    elif 'maintainer' in pkg or 'specification' in pkg:
                        status_str = 'un'
                    else:
                        status_str = 'ii'

                if status_str == 'ii':
                    if 'maintainer' not in pkg and 'specification' not in pkg:
                        styled_status = '[dim]ii[/dim]'
                    else:
                        styled_status = '[success]ii[/success]'
                elif 'h' in status_str or status_str.startswith('r'):
                    styled_status = f'[error]{status_str}[/error]'
                elif status_str == 'un':
                    styled_status = '[warning]un[/warning]'
                else:
                    styled_status = status_str

                table.add_row(styled_status, pkg['name'], pkg['version'], pkg['description'] or '')

            self.console.print(table)

    def search_packages(self, query: Optional[str] = None, summary: bool = False) -> None:
        logger.debug('Searching packages with query: %s', query)
        if not self._repository_info:
            self.update_local_repo_info()

        if not self._repository_info:
            return

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

        if not ret and not self.quiet:
            self.console.print(f'[warning]No packages found matching "{query}"[/warning]')
            return

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

    def show_info(self, package_name: str) -> None:
        """Shows detailed information about a package."""
        logger.debug('Showing info for package: %s', package_name)
        if not self._repository_info:
            self.update_local_repo_info()

        # Try to find the package in the repository
        try:
            package_status = get_installed_package_status(package_name)
            # If installed/available locally, get the version
            if package_status:
                latest_version = next(iter(package_status.keys()))
            else:
                # Get latest version from repo
                if package_name not in self._repository_info:
                    raise KeyError(f'Package {package_name} not found in repository.')

                versions = list(self._repository_info[package_name].keys())
                versions.sort(key=packaging.version.parse, reverse=True)
                latest_version = versions[0]

            metadata = self._get_package_metadata(package_name, latest_version)

        except (ValueError, KeyError, FileNotFoundError):
            # Fallback if _get_package_metadata fails
            logger.warning('Could not retrieve full metadata for %s', package_name)
            raise

        if not self.quiet:
            table = Table(title=f'Package Information: {package_name}', show_header=False, box=None)
            table.add_column('Field', style='bold cyan')
            table.add_column('Value')

            table.add_row('Name', metadata.get('name', 'N/A'))
            table.add_row('Version', metadata.get('version', 'N/A'))
            table.add_row('Specification', metadata.get('specification', 'N/A'))
            table.add_row('Maintainer', metadata.get('maintainer', 'N/A'))
            table.add_row('Description', metadata.get('description', 'N/A'))

            deps = metadata.get('dependencies', [])
            table.add_row('Dependencies', ', '.join(deps) if deps else 'None')

            self.console.print(table)

    def show_status(self, package_name: str, status: Dict[str, Any]) -> None:
        self.update_local_repo_info()
        version = next(iter(status.keys()))

        try:
            metadata = self._get_package_metadata(package_name, version)
            for key, value in metadata.items():
                if key == 'metadata':
                    # Skip nested metadata if present, or flatten it
                    continue
                self.console.print(f'[bold]{key.capitalize()}:[/bold] {value}')
        except (KeyError, FileNotFoundError, json.JSONDecodeError):
            # Fallback if metadata unavailable
            self.console.print(f'[bold]Name:[/bold] {package_name}')
            self.console.print(f'[bold]Version:[/bold] {version}')

        self.console.print(
            f'Desired Status: [bold]({status[version]["status"]["desired"]})[/bold]'
            f' {STATUS_DESIRED[status[version]["status"]["desired"]]}'
        )
        self.console.print(
            f'Current Status: [bold]({status[version]["status"]["current"]})[/bold]'
            f' {STATUS_CURRENT[status[version]["status"]["current"]]}'
        )

        if 'install_date' in status[version]:
            self.console.print(f'[bold]Install Date:[/bold] {status[version]["install_date"]}')

        if 'remove_date' in status[version]:
            self.console.print(f'[bold]Remove Date:[/bold] {status[version]["remove_date"]}')

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

    def list_package_files(self, package_name: str) -> None:
        """List the files installed by a package (analogous to 'dpkg -L')."""
        logger.debug('Listing installed files for package: %s', package_name)

        try:
            get_installed_package_status(package_name)
        except ValueError:
            raise ValueError(f'Package {package_name} is not installed.') from None

        list_file = os.path.join(PKG_INFO_PATH, f'{package_name}.list')

        if not os.path.isfile(list_file):
            return

        with open(list_file, encoding='utf-8') as f:
            for line in f:
                path = line.strip()
                if path:
                    self.console.print(path)
