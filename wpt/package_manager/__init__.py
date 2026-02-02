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

"""PackageManager module - composed from mixin classes."""

from .base import PackageManagerBase
from .build import BuildMixin
from .install import InstallMixin
from .query import QueryMixin
from .registry import RegistryMixin
from .remove import RemoveMixin
from .repository import RepositoryMixin


class PackageManager(
    RepositoryMixin,
    InstallMixin,
    RemoveMixin,
    QueryMixin,
    BuildMixin,
    RegistryMixin,
    PackageManagerBase,
):
    """Complete PackageManager class composed from mixin classes.

    Mixins are listed in order of precedence (first wins for method resolution).
    PackageManagerBase must be last as it contains __init__.
    """

    pass


__all__ = ['PackageManager']
