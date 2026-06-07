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
from rich.table import Table

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

    def show_config(self) -> None:
        """Display configuration information, active files, and values with origins."""

        # 1. Print loaded configuration files
        self.console.print('[header]Configuration Files Loaded (in order of precedence):[/header]')
        self.console.print('  - [info]\\[default][/info] (Internal Defaults)')
        if not self.config.loaded_files:
            self.console.print('  [warning]No configuration files were found/loaded on disk.[/warning]')
        else:
            for idx, file_path in enumerate(self.config.loaded_files, 1):
                self.console.print(f'  {idx}. [info]{file_path}[/info]')
        self.console.print()

        # 2. Print effective configuration key/value table
        table = Table(title='Effective Configuration', show_header=True, header_style='bold magenta')
        table.add_column('Key', style='pkg.name')
        table.add_column('Value', style='pkg.version')
        table.add_column('Origin', style='italic blue')

        parser = self.config._parser
        for section in sorted(parser.sections()):
            for option in sorted(parser.options(section)):
                val = parser.get(section, option)
                origin = self.config.origins.get((section, option), 'default')
                table.add_row(f'{section}.{option}', val, origin)

        self.console.print(table)
