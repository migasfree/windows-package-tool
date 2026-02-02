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

"""Registry operations mixin for PackageManager."""

import contextlib
from typing import Any, Dict

with contextlib.suppress(ImportError):
    import winreg

from ..settings import PMS


class RegistryMixin:
    """Mixin class for Windows registry operations."""

    def add_package_metadata_to_registry(self, metadata: Dict[str, Any]) -> None:
        with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, f'SOFTWARE\\{PMS}\\Packages') as key:  # noqa: SIM117
            with winreg.CreateKey(key, metadata['name']) as subkey:
                winreg.SetValueEx(subkey, 'Name', 0, winreg.REG_SZ, metadata['name'])
                winreg.SetValueEx(subkey, 'Version', 0, winreg.REG_SZ, metadata['version'])
                winreg.SetValueEx(subkey, 'Description', 0, winreg.REG_SZ, metadata['description'])
                winreg.SetValueEx(subkey, 'Maintainer', 0, winreg.REG_SZ, metadata['maintainer'])
                winreg.SetValueEx(subkey, 'Specification', 0, winreg.REG_SZ, metadata['specification'])

    def remove_package_metadata_from_registry(self, package_name: str) -> None:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f'SOFTWARE\\{PMS}\\Packages', 0, winreg.KEY_ALL_ACCESS) as key:
            winreg.DeleteKey(key, package_name)
