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
        assert captured.out == ''


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
