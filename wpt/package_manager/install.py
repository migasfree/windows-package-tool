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

"""Install operations mixin for PackageManager."""

import os
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional

import packaging.version
from rich.prompt import Confirm

from ..logging import logger
from ..settings import PKG_INFO_PATH, PMS_PACKAGES_PATH, PMS_TEMP_PATH
from ..utils import (
    check_app_dirs,
    check_version_condition,
    create_package_info,
    delete_files_with_pattern,
    extract_tar_gz,
    is_dependency_installed,
    is_package_installed,
    parse_dependency,
    parse_version,
    run_script,
    update_package_status,
)


class InstallMixin:
    """Mixin class for install operations.

    Cross-mixin dependencies:
        - RepositoryMixin: update_local_repo_info(), download_package(),
          _get_package_metadata(), _repository_info
        - RegistryMixin: add_package_metadata_to_registry()
        - RemoveMixin: remove_package() (used by upgrade())
        - QueryMixin: get_installed_packages() (used by upgrade())
    """

    def configure_package(self, metadata: Dict[str, Any]) -> None:
        logger.info('Configuring package %s...', metadata['name'])

        create_package_info(PMS_TEMP_PATH, metadata['name'])

        pms_path = os.path.join(PMS_TEMP_PATH, metadata['name'], 'pms')
        data_path = os.path.join(PMS_TEMP_PATH, metadata['name'], 'data')
        install_dir = os.path.join(PMS_PACKAGES_PATH, metadata['name'])

        # Managed Install: Copy data files to standard location
        if os.path.isdir(data_path):
            if os.path.exists(install_dir):
                shutil.rmtree(install_dir)
            shutil.copytree(data_path, install_dir)
            logger.debug('Copied data files to %s', install_dir)

        pkg_list_file = os.path.join(PKG_INFO_PATH, f'{metadata["name"]}.list')
        env = {'WPT_INSTALL_DIR': install_dir, 'WPT_PKG_LIST': pkg_list_file}

        update_package_status(metadata['name'], metadata['version'], desired='i', current='h')

        try:
            run_script(os.path.join(pms_path, 'preinst'), env=env)
            run_script(os.path.join(pms_path, 'install'), env=env)
            run_script(os.path.join(pms_path, 'postinst'), env=env)
        except RuntimeError as e:
            logger.error('Installation failed. Rolling back changes for %s...', metadata['name'])

            # Rollback: Remove managed files
            if os.path.exists(install_dir):
                shutil.rmtree(install_dir, ignore_errors=True)
                logger.debug('Rolled back managed files at %s', install_dir)

            # Rollback: Remove metadata info
            delete_files_with_pattern(PKG_INFO_PATH, metadata['name'])
            logger.debug('Rolled back metadata files')

            # Rollback: Revert status
            update_package_status(metadata['name'], metadata['version'], desired='u', current='n')

            raise RuntimeError(f'Package configuration failed (rolled back): {e}') from e

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

        # Filter out packages that the user has already confirmed to install in a parent prompt
        unconfirmed_packages = {
            name: version for name, version in packages.items() if name not in self._confirmed_packages
        }

        if not self.assume_yes and unconfirmed_packages:
            self.console.print('[warning]The following packages will also be installed:[/warning]')
            for name, version in unconfirmed_packages.items():
                self.console.print(f' - {name} ({version})')

            if not Confirm.ask('Are you sure you want to continue?', default=True, console=self.console):
                raise RuntimeError('Operation cancelled by user.')

        # Mark all of them as confirmed
        self._confirmed_packages.update(packages.keys())

        for package_name, package_version in packages.items():
            if not is_package_installed(package_name, package_version):
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

        # Ensure all application directories exist (especially after remove_package renames them)
        check_app_dirs()

        installed_packages = {item['name']: item['version'] for item in self.get_installed_packages()}

        package_metadata = self._get_package_metadata(package_name, package_version)
        update_package_status(package_metadata['name'], package_metadata['version'], desired='i', current='n')

        if os.path.isfile(package_name):
            target = os.path.join(PMS_TEMP_PATH, os.path.basename(package_name))
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
        shutil.rmtree(path, ignore_errors=True)
        if os.path.exists(target):
            try:
                os.remove(target)
            except Exception as e:
                logger.warning('Failed to remove temporary package archive %s: %s', target, e)

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
        Resolves package dependencies iteratively.

        Uses a work queue instead of recursion to avoid RecursionError
        with deeply nested or malicious dependency chains.

        Args:
            package_name (str)
            package_version (str)
            installed_packages (dict): ({name1: version1, name2: version2, ...})
            processed_packages (dict): Reserved for API compatibility (ignored).

        Raises:
            ValueError: if circular dependency is detected
        """
        if installed_packages is None:
            installed_packages = {}

        resolved = {}  # type: Dict[str, str]
        # Work queue: list of (name, version, path) to process
        pending = [(package_name, package_version, frozenset())]  # type: List

        while pending:
            current_name, current_version, path = pending.pop(0)

            if current_name in path:
                raise ValueError(f'Circular dependency detected: {current_name}')

            if current_name in resolved:
                continue

            resolved[current_name] = current_version

            package_metadata = self._get_package_metadata(current_name, current_version)
            dependencies = package_metadata.get('dependencies', [])

            new_path = path | {current_name}

            for dependency in dependencies:
                dependency_name, dependency_version = parse_dependency(dependency)
                condition, version = parse_version(dependency_version)

                if is_dependency_installed(dependency_name, condition, version, installed_packages):
                    continue

                if dependency_name in new_path:
                    raise ValueError(f'Circular dependency detected: {dependency_name}')

                dep_version = self._get_latest_dependency_version(dependency_name, version, condition)
                pending.append((dependency_name, str(dep_version), new_path))

        installed_packages.update(resolved)
        return installed_packages

    def upgrade(self, installed_packages: Optional[List[Dict[str, Any]]] = None) -> Dict[str, str]:
        logger.info('Starting upgrade process')
        if installed_packages is None:
            installed_packages = self.get_installed_packages()

        logger.debug('Checking %d installed packages for upgrades', len(installed_packages))
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
                    # 1. Download and verify the package first to ensure network/SSL success
                    # We download to system temp directory to prevent directory rename conflicts
                    import tempfile

                    package_metadata = self._get_package_metadata(package['name'], latest_version)
                    target = self.download_package(package_metadata, target_dir=tempfile.gettempdir())

                    # 2. Once downloaded successfully, remove the old package version
                    self.remove_package(package['name'], force=True)

                    # 3. Install the new package using the downloaded target file
                    self.install_package(target)

                    # Add to upgraded dictionary
                    upgraded[package['name']] = latest_version

        if not upgraded and not self.quiet:
            self.console.print('No packages to upgrade.')

        return upgraded
