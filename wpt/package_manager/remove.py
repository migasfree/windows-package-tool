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

"""Remove operations mixin for PackageManager."""

import json
import os
import shutil
from datetime import datetime
from typing import Any, Dict

from rich.prompt import Confirm

from ..logging import logger
from ..settings import (
    PKG_INFO_PATH,
    PKG_METADATA_FILE,
    PMS_PACKAGES_PATH,
    PMS_TEMP_PATH,
    REPO_LOCAL_PATH,
)
from ..utils import (
    delete_files_with_pattern,
    get_installed_package_status,
    is_package_installed,
    run_script,
    update_package_status,
)


class RemoveMixin:
    """Mixin class for remove operations.

    Cross-mixin dependencies:
        - RepositoryMixin: update_local_repo_info(), _repository_info
        - RegistryMixin: remove_package_metadata_from_registry()
        - InstallMixin: resolve_dependencies()
        - QueryMixin: get_installed_packages()
    """

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

    def deconfigure_package(self, metadata: Dict[str, Any]) -> None:
        logger.info('Removing package %s_%s...', metadata['name'], metadata['version'])

        update_package_status(metadata['name'], metadata['version'], desired='r', current='i')
        self.remove_package_metadata_from_registry(metadata['name'])
        update_package_status(metadata['name'], metadata['version'], desired='r', current='h')

        path = os.path.join(PKG_INFO_PATH, metadata['name'])
        install_dir = os.path.join(PMS_PACKAGES_PATH, metadata['name'])
        env = {'WPT_INSTALL_DIR': install_dir, 'WPT_PKG_LIST': f'{path}.list'}

        try:
            run_script(f'{path}.prerm', env=env)
            run_script(f'{path}.remove', env=env)
            run_script(f'{path}.postrm', env=env)
        except RuntimeError as e:
            raise RuntimeError(f'Package deconfiguration failed: {e}') from e

        # Remove the package files using the manifest list
        list_file = f'{path}.list'
        if os.path.isfile(list_file):
            with open(list_file) as f:
                for line in f:
                    file_path = line.strip()
                    if not os.path.isabs(file_path):
                        file_path = os.path.join(install_dir, file_path)
                    if os.path.isfile(file_path):
                        try:
                            os.remove(file_path)
                        except OSError as e:
                            logger.warning('Failed to remove file %s: %s', file_path, e)

            # Remove the install directory if empty or just try to remove it recursively if pure managed
            # Since we copy data/* to install_dir, we can just remove install_dir usually.
            # But adhering to .list is safer if mixed content, though we just copied it entirely.
            if os.path.isdir(install_dir):
                shutil.rmtree(install_dir, ignore_errors=True)

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
        try:
            package_metadata = self._repository_info[package_name][package_version]['metadata']
        except KeyError:
            try:
                with open(os.path.join(PKG_INFO_PATH, f'{package_name}.{PKG_METADATA_FILE}')) as f:
                    package_metadata = json.load(f)
            except Exception as e:
                raise ValueError(
                    f'Metadata for package {package_name} (version {package_version}) not found locally or in repository: {e}'
                ) from e

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

    def clean(self) -> None:
        logger.info('Cleaning temporary files and cache')
        if os.path.isdir(PMS_TEMP_PATH):
            shutil.rmtree(PMS_TEMP_PATH)
        os.makedirs(PMS_TEMP_PATH, exist_ok=True)
        if not self.quiet:
            self.console.print(f'Temporal path cleaned: [bold]{PMS_TEMP_PATH}[/bold]')
        if os.path.isfile(REPO_LOCAL_PATH):
            os.remove(REPO_LOCAL_PATH)
            if not self.quiet:
                self.console.print(f'File [bold]{REPO_LOCAL_PATH}[/bold] removed')
