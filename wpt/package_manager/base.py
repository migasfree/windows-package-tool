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

"""Base class for PackageManager with shared state and configuration."""

from typing import Any, Dict, Union

from rich.console import Console

from ..config import get_config
from ..settings import THEME


class PackageManagerBase:
    """Base class with shared state and initialization."""

    _repository_info: Dict[str, Any] = {}  # noqa: RUF012

    def __init__(
        self,
        quiet: bool = False,
        assume_yes: bool = False,
        verify: Union[bool, str, None] = None,
    ) -> None:
        self.quiet = quiet
        self.assume_yes = assume_yes

        self.config = get_config()
        self.verify = self.config.ssl_verify if verify is None else verify

        self.console = Console(quiet=self.quiet, theme=THEME)
