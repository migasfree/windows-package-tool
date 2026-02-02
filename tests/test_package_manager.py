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


class TestDownloadPackage:
    """Tests for package downloading and verification."""

    def test_download_success(self, pms, mocker, tmp_path):
        metadata = {
            'name': 'test-pkg',
            'version': '1.0',
            'url': 'http://repo.com',
        }
        pms._repository_info = {'test-pkg': {'1.0': {'filename': 'pkg.tar.gz', 'hash': 'hash123'}}}

        # Mock requests
        mock_response = MagicMock()
        mock_response.headers.get.return_value = '100'
        mock_response.iter_content.return_value = [b'data']
        mocker.patch('wpt.package_manager.requests.get', return_value=mock_response)

        # Mock file writing
        mock_open = mocker.patch('builtins.open', mocker.mock_open())

        # Mock hash verification
        mocker.patch('wpt.package_manager.verify_hash')

        target = pms.download_package(metadata)
        # The file name is constructed from metadata, ignoring repo filename
        assert 'test-pkg_1.0_x64.tar.gz' in str(target)
        mock_open.assert_called()

    def test_download_hash_mismatch(self, pms, mocker):
        metadata = {'name': 'pkg', 'version': '1.0', 'url': 'http://r'}
        pms._repository_info = {'pkg': {'1.0': {'filename': 'f', 'hash': 'h'}}}

        mocker.patch('wpt.package_manager.requests.get', return_value=MagicMock())
        mocker.patch('builtins.open', mocker.mock_open())

        mocker.patch('wpt.package_manager.verify_hash', side_effect=ValueError('Bad hash'))

        with pytest.raises(ValueError, match='verification failed'):
            pms.download_package(metadata)


class TestBuild:
    """Tests for package building."""

    def test_build_success(self, pms, mocker, tmp_path):
        pkg_dir = tmp_path / 'mypkg'
        pms_dir = pkg_dir / 'pms'
        pms_dir.mkdir(parents=True)
        # Create real file so open() works without mocking it
        (pms_dir / 'metadata.json').write_text(
            json.dumps(
                {
                    'name': 'mypkg',
                    'version': '1.0',
                    'specification': '1.0.0',
                    'maintainer': 'me',
                    'description': 'desc',
                    'dependencies': [],
                }
            )
        )
        (pms_dir / 'install.cmd').touch()
        (pms_dir / 'remove.cmd').touch()

        # Mock tarfile to create a dummy file at the EXPECTED DESTINATION
        # avoiding issues with cwd/shutil.move in test environment
        def side_effect_tar_open(name, *args, **kwargs):
            # name is relative 'mypkg_1.0_x64.tar.gz'
            # Code creates it in pkg_dir, then moves to '..' (tmp_path)
            # We simulate the final state: file exists in tmp_path
            # We also need to create it in current dir (pkg_dir) if shutil.move is NOT mocked,
            # so it has something to move?
            # If we don't mock shutil.move, it will try to move.
            # So creating in pkg_dir is safer if we let shutil run.
            with open(tmp_path / name, 'wb') as f:
                f.write(b'dummy content')
            with open(name, 'wb') as f:
                f.write(b'dummy content')
            return mocker.MagicMock()

        mocker.patch('tarfile.open', side_effect=side_effect_tar_open)
        mocker.patch('wpt.package_manager.shutil.move')  # Mock move since we create in dest
        mocker.patch('hashlib.sha256').return_value.hexdigest.return_value = 'hash123'

        mocker.patch('wpt.package_manager.check_metadata_content')

        pkg_file, pkg_hash = pms.build(str(pkg_dir))

        assert 'mypkg_1.0' in pkg_file
        assert pkg_hash == 'hash123'

    def test_build_missing_metadata(self, pms, tmp_path):
        pkg_dir = tmp_path / 'mypkg'
        pms_dir = pkg_dir / 'pms'
        pms_dir.mkdir(parents=True)

        with pytest.raises(ValueError, match='file does not exist'):
            pms.build(str(pkg_dir))

    def test_build_missing_scripts(self, pms, tmp_path, mocker):
        pkg_dir = tmp_path / 'mypkg'
        pms_dir = pkg_dir / 'pms'
        pms_dir.mkdir(parents=True)
        # Create data directory to trigger script validation
        (pkg_dir / 'data').mkdir()

        # Fix file name here too
        (pms_dir / 'metadata.json').write_text(
            json.dumps(
                {
                    'name': 'mypkg',
                    'version': '1.0',
                    'specification': '1.0.0',
                    'maintainer': 'me',
                    'description': 'desc',
                    'dependencies': [],
                }
            )
        )

        # We don't mock os.path functions, relying on real FS
        with pytest.raises(ValueError, match='install and/or remove file'):
            pms.build(str(pkg_dir))


class TestInstallPackage:
    """Tests for package installation."""

    def test_install_simple_success(self, pms, mocker):
        # Mock everything needed for a clean install
        pms._repository_info = {'pkg': {'1.0': {'metadata': {'name': 'pkg', 'version': '1.0', 'dependencies': []}}}}
        mocker.patch.object(pms, 'update_local_repo_info')
        mocker.patch.object(pms, 'get_installed_packages', return_value=[])
        mocker.patch.object(pms, 'download_package', return_value='/tmp/pkg.tar.gz')
        mocker.patch('wpt.package_manager.extract_tar_gz')
        mocker.patch('wpt.package_manager.shutil.rmtree')
        mocker.patch('wpt.package_manager.os.remove')
        mocker.patch('wpt.package_manager.os.path.isfile', return_value=False)
        mocker.patch('wpt.package_manager.update_package_status')
        mocker.patch.object(pms, 'configure_package')

        pms.install_package('pkg')

        pms.configure_package.assert_called_once()
        pms.download_package.assert_called_once()


class TestRemovePackage:
    """Tests for package removal."""

    def test_remove_success(self, pms, mocker):
        mocker.patch('wpt.package_manager.get_installed_package_status', return_value={'1.0': {}})
        mocker.patch.object(pms, 'update_local_repo_info')
        pms._repository_info = {'pkg': {'1.0': {'metadata': {'name': 'pkg', 'version': '1.0'}}}}

        mocker.patch.object(pms, 'get_installed_packages', return_value=[])
        mocker.patch.object(pms, 'deconfigure_package')

        pms.remove_package('pkg')
        pms.deconfigure_package.assert_called_once()

    def test_remove_blocked_by_dependency(self, pms, mocker):
        mocker.patch('wpt.package_manager.get_installed_package_status', return_value={'1.0': {}})
        mocker.patch.object(pms, 'update_local_repo_info')
        pms._repository_info = {'pkg': {'1.0': {'metadata': {'name': 'pkg', 'version': '1.0'}}}}

        mock_winreg = mocker.patch('wpt.package_manager.winreg', create=True)
        mock_winreg.OpenKey.return_value.__enter__.return_value = mocker.Mock()
        mock_winreg.QUERY_INFO_KEY = 0

        mocker.patch.object(pms, 'resolve_dependencies', side_effect=ValueError('Blocked'))

        with pytest.raises(ValueError, match='unmet dependencies'):
            pms.remove_package('pkg')

    def test_remove_forced(self, pms, mocker):
        mocker.patch('wpt.package_manager.get_installed_package_status', return_value={'1.0': {}})
        mocker.patch.object(pms, 'update_local_repo_info')
        pms._repository_info = {'pkg': {'1.0': {'metadata': {'name': 'pkg', 'version': '1.0'}}}}

        # Mock winreg
        mock_winreg = mocker.patch('wpt.package_manager.winreg', create=True)
        mock_winreg.OpenKey.return_value.__enter__.return_value = mocker.Mock()

        mocker.patch.object(
            pms, 'get_installed_packages', return_value=[{'name': 'app', 'version': '2.0', 'dependencies': ['pkg']}]
        )
        mocker.patch.object(pms, 'deconfigure_package')

        # Should succeed despite dependency
        pms.remove_package('pkg', force=True)
        pms.deconfigure_package.assert_called_once()
