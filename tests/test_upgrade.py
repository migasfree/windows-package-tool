import tempfile
from unittest.mock import MagicMock

import pytest

from wpt.package_manager import PackageManager


@pytest.fixture
def pms():
    pms = PackageManager()
    pms.install_package = MagicMock()
    pms.remove_package = MagicMock()
    pms.download_package = MagicMock(return_value='dummy_package_file.tar.gz')
    return pms


def test_upgrade(pms):
    installed_packages = [
        {
            'name': 'package-a',
            'version': '1.0.0',
        },
        {'name': 'package-b', 'version': '2.0.0'},
    ]
    pms._repository_info = {
        'package-a': {'1.0.0': {'metadata': {}}, '2.0.0': {'metadata': {}}},
        'package-b': {'2.0.0': {'metadata': {}}, '3.0.0': {'metadata': {}}},
    }

    result = pms.upgrade(installed_packages)
    assert result == {'package-a': '2.0.0', 'package-b': '3.0.0'}
    assert pms.remove_package.call_count == 2
    assert pms.install_package.call_count == 2
    pms.install_package.assert_any_call('dummy_package_file.tar.gz')
    pms.download_package.assert_any_call(
        pms._repository_info['package-a']['2.0.0']['metadata'], target_dir=tempfile.gettempdir()
    )


def test_upgrade_no_upgrades_available(pms):
    """Test that upgrade returns empty when no updates are available."""
    pms.console.print = MagicMock()
    installed_packages = [
        {'name': 'package-a', 'version': '1.0.0'},
    ]
    pms._repository_info = {
        'package-a': {'1.0.0': {'metadata': {}}},  # Same version, no upgrade
    }

    result = pms.upgrade(installed_packages)
    assert result == {}
    assert pms.remove_package.call_count == 0
    assert pms.install_package.call_count == 0
    pms.console.print.assert_called_once_with('No packages to upgrade.')


def test_upgrade_empty_installed_packages(pms):
    """Test that upgrade handles empty installed packages list."""
    pms.console.print = MagicMock()
    pms._repository_info = {
        'package-a': {'1.0.0': {'metadata': {}}},
    }
    # Pass an explicit empty list to avoid calling get_installed_packages
    result = pms.upgrade(installed_packages=[])
    assert result == {}
    assert pms.remove_package.call_count == 0
    assert pms.install_package.call_count == 0
    pms.console.print.assert_called_once_with('No packages to upgrade.')


def test_upgrade_quiet_no_print(pms):
    """Test that upgrade does not print console messages if quiet is True."""
    pms.quiet = True
    pms.console.quiet = True
    pms.console.print = MagicMock()
    pms._repository_info = {
        'package-a': {'1.0.0': {'metadata': {}}},
    }
    result = pms.upgrade(installed_packages=[])
    assert result == {}
    pms.console.print.assert_not_called()
