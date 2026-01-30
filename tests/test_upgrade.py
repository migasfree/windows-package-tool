from unittest.mock import MagicMock

import pytest

from wpt.package_manager import PackageManager


@pytest.fixture
def pms():
    pms = PackageManager()
    pms.install_package = MagicMock()
    pms.remove_package = MagicMock()
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


def test_upgrade_no_upgrades_available(pms):
    """Test that upgrade returns empty when no updates are available."""
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


def test_upgrade_empty_installed_packages(pms):
    """Test that upgrade handles empty installed packages list."""
    pms._repository_info = {
        'package-a': {'1.0.0': {'metadata': {}}},
    }
    # Pass an explicit empty list to avoid calling get_installed_packages
    result = pms.upgrade(installed_packages=[])
    assert result == {}
    assert pms.remove_package.call_count == 0
    assert pms.install_package.call_count == 0
