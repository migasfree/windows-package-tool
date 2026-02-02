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

"""Repository operations mixin for PackageManager."""

import json
import os
import shutil
from typing import Any, Dict, List, Optional

import packaging.version
import requests
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from ..logging import logger
from ..settings import (
    PKG_ARCH,
    PKG_EXT,
    PKG_INFO_PATH,
    PKG_METADATA_FILE,
    PMS_TEMP_PATH,
    REPO_FILE,
    REPO_LOCAL_PATH,
    SOURCES_PATH,
)
from ..utils import check_app_dirs, extract_tar_gz, verify_hash


class RepositoryMixin:
    """Mixin class for repository operations."""

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

                # GPG signature verification
                gpg_mode = self.config.gpg_verify if self.config else 'optional'
                if gpg_mode != 'disabled':
                    sig_url = f'{url}/packages.json.sig'
                    try:
                        sig_response = requests.get(sig_url, verify=self.verify)
                        if sig_response.status_code == 200:
                            # Save temporarily for verification
                            import tempfile

                            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                                f.write(response.text)
                                json_path = f.name
                            with tempfile.NamedTemporaryFile(mode='w', suffix='.sig', delete=False) as f:
                                f.write(sig_response.text)
                                sig_path = f.name

                            from ..gpg import verify_signature

                            if verify_signature(json_path, sig_path):
                                logger.info('GPG signature verified for %s', url)
                            else:
                                msg = f'GPG signature verification failed for {url}'
                                if gpg_mode == 'required':
                                    logger.error(msg)
                                    if not self.quiet:
                                        self.console.print(f'[error]{msg}[/error]')
                                    continue
                                else:
                                    logger.warning(msg)
                                    if not self.quiet:
                                        self.console.print(f'[warning]{msg}[/warning]')

                            # Cleanup temp files
                            import os as _os

                            _os.unlink(json_path)
                            _os.unlink(sig_path)
                        else:
                            msg = f'No GPG signature available for {url}'
                            if gpg_mode == 'required':
                                logger.error(msg)
                                if not self.quiet:
                                    self.console.print(f'[error]{msg}[/error]')
                                continue
                            else:
                                logger.debug(msg)
                    except requests.RequestException as e:
                        msg = f'Failed to fetch GPG signature from {url}: {e}'
                        if gpg_mode == 'required':
                            logger.error(msg)
                            continue
                        else:
                            logger.debug(msg)

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

        if not self._repository_info and not self.quiet:
            self.console.print(
                '[warning]Repository data is empty. Update may have failed. Check logs for details.[/warning]'
            )

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

    def download_package(self, metadata: Dict[str, Any], target_dir: str = PMS_TEMP_PATH) -> str:
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

                target = os.path.join(target_dir, f'{metadata["name"]}_{metadata["version"]}_{PKG_ARCH}{PKG_EXT}')
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

    def download(self, package_name: str, output_dir: Optional[str] = None) -> None:
        """Downloads a package without installing it."""
        logger.debug('Downloading package: %s to %s', package_name, output_dir or 'current directory')
        if not self._repository_info:
            self.update_local_repo_info()

        if package_name not in self._repository_info:
            logger.error('Package %s not found in repository', package_name)
            raise KeyError(f'Package {package_name} not found in repository')

        # Get latest version
        versions = list(self._repository_info[package_name].keys())
        versions.sort(key=packaging.version.parse, reverse=True)
        latest_version = versions[0]

        pkg_info = self._repository_info[package_name][latest_version]
        # Metadata needed by download_package: name, version, url
        # And download_package looks up filename/hash from _repository_info internally
        metadata = pkg_info['metadata']

        target_dir = output_dir if output_dir else os.getcwd()
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        downloaded_path = self.download_package(metadata, target_dir)

        if not self.quiet:
            self.console.print(f'[success]Package downloaded successfully to:[/success] {downloaded_path}')
