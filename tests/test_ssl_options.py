import contextlib
from unittest.mock import MagicMock, patch

from wpt.package_manager import PackageManager


def test_init_default_verify():
    pms = PackageManager()
    assert pms.verify is True


def test_init_custom_verify_false():
    pms = PackageManager(verify=False)
    assert pms.verify is False


def test_init_custom_verify_path():
    pms = PackageManager(verify='/path/to/cert.pem')
    assert pms.verify == '/path/to/cert.pem'


@patch('wpt.package_manager.repository.requests.get')
def test_download_package_verify_true(mock_get):
    pms = PackageManager(verify=True)
    pms._repository_info = {'pkg': {'1.0': {'filename': 'pkg.tar.gz'}}}
    metadata = {'name': 'pkg', 'version': '1.0', 'url': 'http://repo'}

    # Mock successful response
    mock_response = MagicMock()
    mock_response.raw = MagicMock()
    mock_get.return_value = mock_response

    with contextlib.suppress(Exception):
        pms.download_package(metadata)

    mock_get.assert_called_with('http://repo/pkg.tar.gz', stream=True, verify=True)


@patch('wpt.package_manager.repository.requests.get')
def test_download_package_verify_false(mock_get):
    pms = PackageManager(verify=False)
    pms._repository_info = {'pkg': {'1.0': {'filename': 'pkg.tar.gz'}}}
    metadata = {'name': 'pkg', 'version': '1.0', 'url': 'http://repo'}

    # Mock successful response
    mock_response = MagicMock()
    mock_response.raw = MagicMock()
    mock_get.return_value = mock_response

    with contextlib.suppress(Exception):
        pms.download_package(metadata)

    mock_get.assert_called_with('http://repo/pkg.tar.gz', stream=True, verify=False)
