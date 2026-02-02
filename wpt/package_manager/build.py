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

"""Build operations mixin for PackageManager."""

import hashlib
import json
import os
import shutil
import tarfile
from typing import Tuple

from ..logging import logger
from ..settings import PKG_ARCH, PKG_EXT, PKG_METADATA_FILE
from ..utils import check_metadata_content


class BuildMixin:
    """Mixin class for package build operations."""

    def build(self, package_directory: str) -> Tuple[str, str]:
        logger.info('Building package from directory: %s', package_directory)
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

        # File is now in the parent of package_directory
        final_path = os.path.join(os.path.dirname(package_directory), package_file)

        with open(final_path, 'rb') as f:
            hash_ = hashlib.sha256(f.read()).hexdigest()

        self.console.print(f'[success]Created package file:[/success] {final_path}')
        self.console.print(f'[dim]Hash:[/dim] {hash_}')

        return final_path, hash_
