import json
from unittest.mock import MagicMock, patch

import pytest

from wpt.package_manager import PackageManager


@pytest.fixture
def pms():
    return PackageManager()


class TestSearchPackages:
    """Tests for the search_packages method."""

    def test_search_all_packages(self, pms, capsys):
        pms._repository_info = {
            'package-a': {'1.0.0': {'metadata': {'description': 'Package A'}}},
            'package-b': {'2.0.0': {'metadata': {'description': 'Package B'}}},
        }
        pms.search_packages()
        captured = capsys.readouterr()
        assert 'package-a' in captured.out
        assert 'package-b' in captured.out

    def test_search_with_query(self, pms, capsys):
        pms._repository_info = {
            'python-tools': {'1.0.0': {'metadata': {'description': 'Tools for Python'}}},
            'java-utils': {'2.0.0': {'metadata': {'description': 'Java utilities'}}},
            'python-requests': {'1.5.0': {'metadata': {'description': 'HTTP requests'}}},
        }
        pms.search_packages(query='python')
        captured = capsys.readouterr()
        assert 'python-tools' in captured.out
        assert 'python-requests' in captured.out
        assert 'java-utils' not in captured.out

    def test_search_by_description(self, pms, capsys):
        pms._repository_info = {
            'http-client': {'1.0.0': {'metadata': {'description': 'HTTP client for Python'}}},
            'ftp-client': {'2.0.0': {'metadata': {'description': 'FTP client'}}},
        }
        pms.search_packages(query='python')
        captured = capsys.readouterr()
        assert 'http-client' in captured.out
        assert 'ftp-client' not in captured.out

    def test_search_no_results(self, pms, capsys):
        pms._repository_info = {
            'package-a': {'1.0.0': {'metadata': {'description': 'Package A'}}},
        }
        pms.search_packages(query='nonexistent')
        captured = capsys.readouterr()
        assert 'No packages found matching "nonexistent"' in captured.out


class TestListInstalledPackages:
    """Tests for the list_installed_packages method."""

    def test_list_summary_mode(self, pms, capsys, mocker):
        mock_list = [
            {'name': 'pkg-a', 'version': '1.0.0'},
            {'name': 'pkg-b', 'version': '2.0.0'},
        ]
        mocker.patch.object(pms, 'get_pms_installed_software', return_value=mock_list)
        pms.list_installed_packages(summary=True)
        captured = capsys.readouterr()
        assert 'pkg-a' in captured.out or 'pkg-b' in captured.out


class TestClean:
    """Tests for the clean method."""

    def test_clean_calls_rmtree(self, pms, mocker):
        mocker.patch('wpt.package_manager.shutil.rmtree')
        mocker.patch('wpt.package_manager.os.makedirs')
        mocker.patch('wpt.package_manager.os.path.isfile', return_value=False)
        pms.clean()
        # Should not raise


class TestGetRepositorySources:
    """Tests for the get_repository_sources method."""

    def test_returns_list_of_sources(self, pms, mocker, tmp_path):
        sources_file = tmp_path / 'sources.json'
        # The function reads lines, not JSON
        sources_file.write_text('https://example.com/repo\nhttps://another.com/repo\n')
        mocker.patch('wpt.package_manager.SOURCES_PATH', str(sources_file))
        result = pms.get_repository_sources()
        assert 'https://example.com/repo' in result
        assert 'https://another.com/repo' in result


class TestRepositoryWarnings:
    """Tests for repository security warnings (SEC-002)."""

    @patch('wpt.package_manager.requests.get')
    @patch('wpt.package_manager.check_app_dirs')
    @patch('wpt.package_manager.logger')
    def test_insecure_repo_warning(self, mock_logger, mock_check_dirs, mock_get):
        pms = PackageManager()

        # Mocking single insecure source
        pms.get_repository_sources = MagicMock(return_value=['http://insecure.repo/ stable main'])

        # Mocking response
        mock_response = MagicMock()
        mock_response.text = json.dumps({'pkg': {'1.0': {'metadata': {}}}})
        mock_get.return_value = mock_response

        pms.update_local_repo_info(regenerate=True)

        # Verify warning was called
        mock_logger.warning.assert_called_with('Using insecure repository: %s', 'http://insecure.repo/')

    @patch('wpt.package_manager.requests.get')
    @patch('wpt.package_manager.check_app_dirs')
    @patch('wpt.package_manager.logger')
    def test_secure_repo_no_warning(self, mock_logger, mock_check_dirs, mock_get):
        pms = PackageManager()

        # Mocking secure source
        pms.get_repository_sources = MagicMock(return_value=['https://secure.repo/ stable main'])

        # Mocking response
        mock_response = MagicMock()
        mock_response.text = json.dumps({'pkg': {'1.0': {'metadata': {}}}})
        mock_get.return_value = mock_response

        pms.update_local_repo_info(regenerate=True)

        # Verify warning was NOT called
        mock_logger.warning.assert_not_called()


class TestSearchWarnings:
    """Tests for search command warnings."""

    def test_search_warns_on_empty_repo(self, pms, capsys, mocker):
        pms._repository_info = {}
        # We need update_local_repo_info to run to trigger the warning
        # Mock get_repository_sources to return empty
        mocker.patch.object(pms, 'get_repository_sources', return_value=[])
        # Force "regenerate" logic (bypass local file read)
        mocker.patch('wpt.package_manager.os.path.isfile', return_value=False)
        # Prevent file writing
        mocker.patch('builtins.open', mocker.mock_open())
        mocker.patch('json.dump')

        pms.search_packages(query='test')
        captured = capsys.readouterr()
        assert 'Repository data is empty' in captured.out


class TestStatusReference:
    """Tests for status command logic."""

    def test_status_fallback_to_local_metadata(self, pms, capsys, mocker):
        # Package in status but NOT in repository
        mock_status = {'test-pkg': {'1.0': {'status': {'desired': 'i', 'current': 'i'}}}}
        pms._repository_info = {}

        # Mock _get_package_metadata to return local info
        mocker.patch.object(
            pms, '_get_package_metadata', return_value={'description': 'Local Description', 'metadata': {}}
        )

        pms.show_status('test-pkg', mock_status['test-pkg'])
        captured = capsys.readouterr()
        # Should print description from "local file"
        assert 'Description: Local Description' in captured.out

    def test_status_fallback_basic(self, pms, capsys, mocker):
        # Metadata completely missing (KeyError/FileNotFound)
        mock_status = {'test-pkg': {'1.0': {'status': {'desired': 'i', 'current': 'i'}}}}
        pms._repository_info = {}

        mocker.patch.object(pms, '_get_package_metadata', side_effect=FileNotFoundError)

        pms.show_status('test-pkg', mock_status['test-pkg'])
        captured = capsys.readouterr()
        # Should fallback to basic info
        assert 'Name: test-pkg' in captured.out
        assert 'Version: 1.0' in captured.out


class TestRepoUpdateErrors:
    """Tests for repository update error handling."""

    @patch('wpt.package_manager.requests.get')
    @patch('wpt.package_manager.logger')
    def test_update_handles_json_error(self, mock_logger, mock_get, pms):
        mock_response = MagicMock()
        mock_response.text = '<html>Error 403</html>'
        mock_response.status_code = 403
        mock_get.return_value = mock_response

        # Use partial mock to allow other methods to run.
        # We mock check_app_dirs to avoid FS ops
        with patch('wpt.package_manager.check_app_dirs'), patch(
            'wpt.package_manager.os.path.isfile', return_value=False
        ), patch.object(pms, 'get_repository_sources', return_value=['http://test.repo stable main']), patch(
            'json.loads', side_effect=json.JSONDecodeError('Expecting value', 'doc', 0)
        ):
            # We enforce side effect by patching json.loads because requests.get().json() is not used
            pms.update_local_repo_info()

        mock_logger.error.assert_called()
        mock_logger.debug.assert_called()

        # Iterate over all debug calls to find the one with the HTML content
        found = False
        for call_args in mock_logger.debug.call_args_list:
            args, _ = call_args
            if '<html>Error 403</html>' in args[0] or (len(args) > 1 and '<html>Error 403</html>' in str(args[1])):
                found = True
                break
        assert found, 'HTML error content not found in debug logs'
