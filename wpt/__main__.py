# Copyright (c) 2024 Jose Antonio Chavarría <jachavar@gmail.com>
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

import sys
import argparse
import errno

from . import __version__
from .settings import PROGRAM, PROGRAM_DESC, PMS
from .utils import is_admin, ensure_single_instance
from .package_manager import PackageManager


def parse_args(argv):
    # Define the command-line interface
    parser = argparse.ArgumentParser(prog=PMS, description=PROGRAM_DESC)

    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='perform operations with minimal (or null) output'
    )
    parser.add_argument(
        '-y', '--assume-yes',
        action='store_true',
        help='automatic yes to prompts'
    )

    subparsers = parser.add_subparsers(dest='command')

    # Install command
    install_parser = subparsers.add_parser('install', help='install packages to system')
    install_parser.add_argument('package', nargs='+', help='the name of the package to install')

    # Remove command
    remove_parser = subparsers.add_parser('remove', help='remove packages from system')
    remove_parser.add_argument('package', nargs='+', help='the name of the package to remove')
    remove_parser.add_argument(
        '-f', '--force',
        action='store_true',
        help='forces remove package without check dependencies'
    )

    # List command
    list_parser = subparsers.add_parser('list', help='list installed packages')
    list_parser.add_argument(
        '-a', '--all',
        action='store_true',
        help='list all packages'
    )
    list_parser.add_argument(
        '-s', '--summary',
        action='store_true',
        help='display a summary of the packages'
    )

    # Search command
    search_parser = subparsers.add_parser('search', help='searchs in available packages')
    search_parser.add_argument('query', nargs='?', default='*', help='the search query')
    search_parser.add_argument(
        '-s', '--summary',
        action='store_true',
        help='display a summary of the packages'
    )

    # Upgrade command
    subparsers.add_parser('upgrade', help='upgrades installed packages in system')

    # Update command
    subparsers.add_parser('update', help='reads online repositories and updates local one')

    # Build command
    build_parser = subparsers.add_parser('build', help='creates a PMS package')
    build_parser.add_argument('directory', help='the directory containing package files')

    # Clean command
    subparsers.add_parser('clean', help='cleans PMS cache')

    # Status command
    status_parser = subparsers.add_parser('status', help='returns package status')
    status_parser.add_argument('package', help='the name of the package to check the status of')
    status_parser.add_argument(
        '-i', '--is-installed',
        action='store_true',
        help='return exit code indicating if the package is installed or not'
    )

    if len(argv) < 1:
        parser.print_help()
        sys.exit()

    return parser.parse_args()


def main(argv=None):
    ensure_single_instance()

    if argv is None:
        argv = sys.argv[1:]

    args = parse_args(argv)

    if hasattr(args, 'quiet') and not args.quiet:
        print(f'{PROGRAM} {__version__}\n')
        sys.stdout.flush()

    if args.command in ['install', 'remove', 'update', 'upgrade', 'clean'] and not is_admin():
        print('This command requires administrator privileges.')
        sys.exit(errno.EPERM)

    pms = PackageManager(args.quiet, args.assume_yes)

    # Call the appropriate function based on the command
    if args.command == 'install':
        for package in args.package:
            if '=' in package:
                name, version = package.split('=')
                pms.install_package(name, version)
            else:
                pms.install_package(package)
    elif args.command == 'remove':
        for package in args.package:
            pms.remove_package(package, args.force)
    elif args.command == 'list':
        pms.list_installed_packages(args.all, args.summary)
    elif args.command == 'search':
        pms.search_packages(args.query, args.summary)
    elif args.command == 'update':
        pms.update_local_repo_info(regenerate=True)
    elif args.command == 'upgrade':
        pms.upgrade()
    elif args.command == 'status':
        pms.status(args.package, args.is_installed)
    elif args.command == 'clean':
        pms.clean()
    elif args.command == 'build':
        try:
            pms.build(args.directory)
        except ValueError as e:
            print(e)


if __name__ == '__main__':
    main()
