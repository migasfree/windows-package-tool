import pytest

from wpt.package_manager import PackageManager


@pytest.fixture
def pms():
    return PackageManager()


def test_upgrade(pms):
    installed_packages = [
        {
            'name': 'package-a',
            'version': '1.0.0',
        },
        {
            'name': 'package-b',
            'version': '2.0.0'
        }
    ]
    pms._repository_info = {
        'package-a': {
            '1.0.0': {'metadata': {}},
            '2.0.0': {'metadata': {}}
        },
        'package-b': {
            '2.0.0': {'metadata': {}},
            '3.0.0': {'metadata': {}}
        }
    }

    result = pms.upgrade(installed_packages)
    assert result == {'package-a': '2.0.0', 'package-b': '3.0.0'}
