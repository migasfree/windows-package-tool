import sys

import pytest
from packaging.version import Version

from wpt.utils import (
    check_dependency,
    check_metadata_content,
    check_version_condition,
    is_dependency_installed,
    parse_dependency,
    parse_version,
)


class TestParseDependency:
    """Tests for the parse_dependency function."""

    def test_simple_name(self):
        name, version = parse_dependency('my-package')
        assert name == 'my-package'
        assert version is None

    def test_name_with_version(self):
        name, version = parse_dependency('my-package (>= 1.0.0)')
        assert name == 'my-package'
        assert version == '(>= 1.0.0)'

    def test_name_with_exact_version(self):
        name, version = parse_dependency('another-pkg (= 2.5.0)')
        assert name == 'another-pkg'
        assert version == '(= 2.5.0)'


class TestParseVersion:
    """Tests for the parse_version function."""

    def test_none_version(self):
        condition, version = parse_version(None)
        assert condition == '='
        assert version is None

    def test_empty_string(self):
        condition, version = parse_version('')
        assert condition == '='
        assert version is None

    def test_valid_condition(self):
        condition, version = parse_version('(>= 1.2.3)')
        assert condition == '>='
        assert version == '1.2.3'

    def test_less_than_condition(self):
        condition, version = parse_version('(< 2.0.0)')
        assert condition == '<'
        assert version == '2.0.0'


class TestCheckVersionCondition:
    """Tests for the check_version_condition function."""

    def test_equal(self):
        assert check_version_condition(Version('1.0.0'), '=', Version('1.0.0')) is True
        assert check_version_condition(Version('1.0.0'), '=', Version('2.0.0')) is False

    def test_greater_than(self):
        assert check_version_condition(Version('2.0.0'), '>', Version('1.0.0')) is True
        assert check_version_condition(Version('1.0.0'), '>', Version('2.0.0')) is False

    def test_less_than(self):
        assert check_version_condition(Version('1.0.0'), '<', Version('2.0.0')) is True
        assert check_version_condition(Version('2.0.0'), '<', Version('1.0.0')) is False

    def test_greater_than_or_equal(self):
        assert check_version_condition(Version('2.0.0'), '>=', Version('1.0.0')) is True
        assert check_version_condition(Version('1.0.0'), '>=', Version('1.0.0')) is True
        assert check_version_condition(Version('0.9.0'), '>=', Version('1.0.0')) is False

    def test_less_than_or_equal(self):
        assert check_version_condition(Version('1.0.0'), '<=', Version('2.0.0')) is True
        assert check_version_condition(Version('1.0.0'), '<=', Version('1.0.0')) is True
        assert check_version_condition(Version('2.0.0'), '<=', Version('1.0.0')) is False

    def test_unknown_condition(self):
        assert check_version_condition(Version('1.0.0'), '!=', Version('1.0.0')) is False


class TestCheckDependency:
    """Tests for the check_dependency function."""

    def test_equal_pass(self):
        assert check_dependency('pkg', Version('1.0.0'), '=', Version('1.0.0')) is True

    def test_equal_fail(self):
        with pytest.raises(ValueError, match=r'but version 2\.0\.0 is required'):
            check_dependency('pkg', Version('1.0.0'), '=', Version('2.0.0'))

    def test_greater_than_pass(self):
        assert check_dependency('pkg', Version('3.0.0'), '>', Version('2.0.0')) is True

    def test_greater_than_fail(self):
        with pytest.raises(ValueError, match='greater than'):
            check_dependency('pkg', Version('1.0.0'), '>', Version('2.0.0'))

    def test_greater_or_equal_pass(self):
        assert check_dependency('pkg', Version('2.0.0'), '>=', Version('2.0.0')) is True

    def test_greater_or_equal_fail(self):
        with pytest.raises(ValueError, match='greater than or equal to'):
            check_dependency('pkg', Version('1.0.0'), '>=', Version('2.0.0'))

    def test_less_than_pass(self):
        assert check_dependency('pkg', Version('1.0.0'), '<', Version('2.0.0')) is True

    def test_less_than_fail(self):
        with pytest.raises(ValueError, match='less than'):
            check_dependency('pkg', Version('3.0.0'), '<', Version('2.0.0'))

    def test_less_or_equal_pass(self):
        assert check_dependency('pkg', Version('2.0.0'), '<=', Version('2.0.0')) is True

    def test_less_or_equal_fail(self):
        with pytest.raises(ValueError, match='less than or equal to'):
            check_dependency('pkg', Version('3.0.0'), '<=', Version('2.0.0'))


class TestIsDependencyInstalled:
    """Tests for the is_dependency_installed function."""

    def test_not_installed(self):
        assert is_dependency_installed('unknown-pkg', '>=', '1.0.0', {}) is False

    def test_installed_no_version_required(self):
        assert is_dependency_installed('my-pkg', '=', None, {'my-pkg': '1.0.0'}) is True

    def test_installed_version_matches(self):
        assert is_dependency_installed('my-pkg', '>=', '1.0.0', {'my-pkg': '2.0.0'}) is True

    def test_installed_version_does_not_match(self):
        with pytest.raises(ValueError):
            is_dependency_installed('my-pkg', '>=', '3.0.0', {'my-pkg': '2.0.0'})


class TestCheckMetadataContent:
    """Tests for the check_metadata_content function."""

    def test_valid_metadata(self):
        metadata = {
            'name': 'test-package',
            'version': '1.0.0',
            'maintainer': 'Test <test@example.com>',
            'description': 'A test package',
            'specification': '1.0.0',
        }
        # Should not raise
        check_metadata_content(metadata)

    def test_missing_required_key(self):
        metadata = {
            'name': 'test-package',
            'version': '1.0.0',
            # missing maintainer
            'description': 'A test package',
            'specification': '1.0.0',
        }
        with pytest.raises(ValueError, match='required key: maintainer'):
            check_metadata_content(metadata)

    def test_invalid_specification(self):
        metadata = {
            'name': 'test-package',
            'version': '1.0.0',
            'maintainer': 'Test <test@example.com>',
            'description': 'A test package',
            'specification': '2.0.0',
        }
        with pytest.raises(ValueError, match=r'must be "1\.0\.0"'):
            check_metadata_content(metadata)

    def test_invalid_dependencies_type(self):
        metadata = {
            'name': 'test-package',
            'version': '1.0.0',
            'maintainer': 'Test <test@example.com>',
            'description': 'A test package',
            'specification': '1.0.0',
            'dependencies': 'not-a-list',
        }
        with pytest.raises(ValueError, match='dependencies value is not a list'):
            check_metadata_content(metadata)

    def test_invalid_dependency_format(self):
        metadata = {
            'name': 'test-package',
            'version': '1.0.0',
            'maintainer': 'Test <test@example.com>',
            'description': 'A test package',
            'specification': '1.0.0',
            'dependencies': ['invalid!!format'],
        }
        with pytest.raises(ValueError, match='not in the expected format'):
            check_metadata_content(metadata)

    def test_valid_dependencies(self):
        metadata = {
            'name': 'test-package',
            'version': '1.0.0',
            'maintainer': 'Test <test@example.com>',
            'description': 'A test package',
            'specification': '1.0.0',
            'dependencies': ['other-pkg (>= 1.0.0)', 'simple-pkg'],
        }
        # Should not raise
        check_metadata_content(metadata)

    def test_valid_pep440_dependencies(self):
        """Test standard and extended PEP 440 versions."""
        cases = [
            'pkg (> 1.0)',
            'pkg (= 1.0.0)',
            'pkg (>= 1.0a1)',  # Alpha
            'pkg (< 1.0.post1)',  # Post-release
            'pkg (<= 1.0.dev1)',  # Dev release
            'pkg-name (> 1!1.0)',  # Epoch
            'simple-pkg',
        ]
        for dep in cases:
            metadata = {
                'name': 'test-package',
                'version': '1.0.0',
                'maintainer': 'Test',
                'description': 'Desc',
                'specification': '1.0.0',
                'dependencies': [dep],
            }
            check_metadata_content(metadata)  # Should not raise

    def test_invalid_pep440_version(self):
        """Test regex passes but packaging.version fails."""
        cases = [
            'pkg (> 1.0.0-invalid)',
            'pkg (= 1.0..0)',
        ]
        for dep in cases:
            metadata = {
                'name': 'test-package',
                'version': '1.0.0',
                'maintainer': 'Test',
                'description': 'Desc',
                'specification': '1.0.0',
                'dependencies': [dep],
            }
            with pytest.raises(ValueError, match='Invalid PEP 440 version'):
                check_metadata_content(metadata)


class TestVerifyHash:
    """Tests for the verify_hash function."""

    def test_valid_hash(self, tmp_path):
        # Create a test file with known content
        test_file = tmp_path / 'test.txt'
        test_file.write_bytes(b'hello world')
        # SHA256 of "hello world"
        expected_hash = 'b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9'
        from wpt.utils import verify_hash

        # Should not raise
        verify_hash(str(test_file), expected_hash)

    def test_invalid_hash(self, tmp_path):
        test_file = tmp_path / 'test.txt'
        test_file.write_bytes(b'hello world')
        from wpt.utils import verify_hash

        with pytest.raises(ValueError, match='Hash mismatch'):
            verify_hash(str(test_file), 'invalid_hash')


class TestExtractTarGz:
    """Tests for the extract_tar_gz function."""

    def test_extract_valid_tarball(self, tmp_path):
        import tarfile

        from wpt.utils import extract_tar_gz

        # Create a tarball
        tarball_path = tmp_path / 'archive.tar.gz'
        content_dir = tmp_path / 'content'
        content_dir.mkdir()
        (content_dir / 'file.txt').write_text('test content')

        with tarfile.open(tarball_path, 'w:gz') as tar:
            tar.add(content_dir / 'file.txt', arcname='file.txt')

        # Extract it
        extract_dir = tmp_path / 'extracted'
        extract_dir.mkdir()
        extract_tar_gz(str(tarball_path), str(extract_dir))

        assert (extract_dir / 'file.txt').exists()


class TestGetExecFile:
    """Tests for the get_exec_file function."""

    def test_python_script_exists(self, tmp_path, monkeypatch):
        from wpt.utils import get_exec_file

        monkeypatch.chdir(tmp_path)
        (tmp_path / 'script.py').write_text('# python')
        result = get_exec_file(str(tmp_path / 'script'))
        assert result == str(tmp_path / 'script.py')

    def test_cmd_script_exists(self, tmp_path, monkeypatch):
        from wpt.utils import get_exec_file

        monkeypatch.chdir(tmp_path)
        (tmp_path / 'script.cmd').write_text('@echo off')
        result = get_exec_file(str(tmp_path / 'script'))
        assert result == str(tmp_path / 'script.cmd')

    def test_ps1_script_exists(self, tmp_path, monkeypatch):
        from wpt.utils import get_exec_file

        monkeypatch.chdir(tmp_path)
        (tmp_path / 'script.ps1').write_text("Write-Host 'test'")
        result = get_exec_file(str(tmp_path / 'script'))
        assert result == str(tmp_path / 'script.ps1')

    def test_no_script_exists(self, tmp_path):
        from wpt.utils import get_exec_file

        result = get_exec_file(str(tmp_path / 'nonexistent'))
        assert result is None


class TestDeleteFilesWithPattern:
    """Tests for the delete_files_with_pattern function."""

    def test_delete_matching_files(self, tmp_path, capsys):
        from wpt.utils import delete_files_with_pattern

        (tmp_path / 'test_1.txt').write_text('content')
        (tmp_path / 'test_2.txt').write_text('content')
        (tmp_path / 'other.txt').write_text('content')

        delete_files_with_pattern(str(tmp_path), 'test_')

        assert not (tmp_path / 'test_1.txt').exists()
        assert not (tmp_path / 'test_2.txt').exists()
        assert (tmp_path / 'other.txt').exists()

    def test_directory_not_exists(self, capsys):
        from wpt.utils import delete_files_with_pattern

        delete_files_with_pattern('/nonexistent/path', 'pattern')
        captured = capsys.readouterr()
        assert 'does not exist' in captured.out


class TestValidateScript:
    """Tests for the validate_script function."""

    def test_valid_script(self, tmp_path):
        from wpt.utils import validate_script

        script = tmp_path / 'test.py'
        script.write_text("print('hello')")
        assert validate_script(str(script)) is True

    def test_script_not_exists(self, tmp_path):
        from wpt.utils import validate_script

        with pytest.raises(ValueError, match='does not exist'):
            validate_script(str(tmp_path / 'nonexistent.py'))

    def test_script_too_large(self, tmp_path):
        from wpt.settings import SCRIPT_MAX_SIZE
        from wpt.utils import validate_script

        script = tmp_path / 'large.py'
        script.write_bytes(b'x' * (SCRIPT_MAX_SIZE + 1))
        with pytest.raises(ValueError, match='too large'):
            validate_script(str(script))

    def test_path_traversal_blocked(self):
        from wpt.utils import validate_script

        with pytest.raises(ValueError, match='does not exist'):
            validate_script('../../../etc/passwd')


class TestRunScriptSecurity:
    """Tests for run_script security features."""

    def test_run_script_with_nonexistent_script(self, tmp_path):
        from wpt.utils import run_script

        # Should return None (no script found)
        result = run_script(str(tmp_path / 'nonexistent'))
        assert result is None

    def test_powershell_uses_execution_policy(self, tmp_path, mocker):
        from wpt.utils import run_script

        script = tmp_path / 'test.ps1'
        script.write_text("Write-Host 'test'")
        mock_run = mocker.patch('wpt.utils.subprocess.run')
        mock_run.return_value.stdout = ''
        run_script(str(tmp_path / 'test'))
        # Verify ExecutionPolicy is set
        call_args = mock_run.call_args[0][0]
        assert '-ExecutionPolicy' in call_args
        assert 'RemoteSigned' in call_args


class TestIsAdmin:
    """Tests for is_admin function."""

    def test_is_admin_true(self, mocker):
        from wpt.utils import is_admin

        mocker.patch('wpt.utils.sys.platform', 'win32')
        # Mock ctypes.windll (create=True for Linux)
        mock_windll = mocker.patch('ctypes.windll', create=True)
        # Configure the mock chain
        mock_windll.shell32.IsUserAnAdmin.return_value = 1
        assert is_admin()

    def test_is_admin_false(self, mocker):
        from wpt.utils import is_admin

        mocker.patch('wpt.utils.sys.platform', 'win32')
        mock_windll = mocker.patch('ctypes.windll', create=True)
        mock_windll.shell32.IsUserAnAdmin.return_value = 0
        assert not is_admin()

    def test_is_admin_exception(self, mocker):
        from wpt.utils import is_admin

        mocker.patch('wpt.utils.sys.platform', 'win32')
        # Simulate error during call
        mock_windll = mocker.patch('ctypes.windll', create=True)
        mock_windll.shell32.IsUserAnAdmin.side_effect = Exception('Error')
        assert is_admin() is False

    def test_is_admin_non_windows(self, mocker):
        from wpt.utils import is_admin

        mocker.patch('wpt.utils.sys.platform', 'linux')
        assert is_admin() is False


class TestCheckAppDirs:
    """Tests for check_app_dirs function."""

    def test_creates_directories(self, mocker):
        from wpt.utils import check_app_dirs

        # Mock paths constants
        mocker.patch('wpt.utils.PMS_DATA_PATH', '/data')
        mocker.patch('wpt.utils.PKG_INFO_PATH', '/info')
        mocker.patch('wpt.utils.PMS_TEMP_PATH', '/temp')
        mocker.patch('wpt.utils.PMS_PACKAGES_PATH', '/packages')
        mocker.patch('wpt.utils.CONF_DIR', '/conf')

        # Mock os
        mocker.patch('os.path.exists', return_value=False)
        mock_makedirs = mocker.patch('os.makedirs')

        check_app_dirs()
        assert mock_makedirs.call_count == 5

    def test_permission_error(self, mocker, capsys):
        import errno

        from wpt.utils import check_app_dirs

        mocker.patch('os.path.exists', return_value=False)
        mocker.patch('os.makedirs', side_effect=PermissionError('Boom'))

        # Should call sys.exit with EACCES
        with pytest.raises(SystemExit) as exc:
            check_app_dirs()

        assert exc.value.code == errno.EACCES
        captured = capsys.readouterr()
        assert 'Insufficient permissions' in captured.out

    def test_os_error(self, mocker, capsys):
        import errno

        from wpt.utils import check_app_dirs

        mocker.patch('os.path.exists', return_value=False)
        mocker.patch('os.makedirs', side_effect=OSError('Boom'))

        with pytest.raises(SystemExit) as exc:
            check_app_dirs()

        assert exc.value.code == errno.EPERM
        captured = capsys.readouterr()
        assert 'Problem creating app directory' in captured.out


class TestEnsureSingleInstance:
    """Tests for ensure_single_instance function."""

    def test_single_instance_success(self, mocker):
        from wpt.utils import ensure_single_instance

        # Mock os.open to return a valid file descriptor
        mocker.patch('os.open', return_value=123)
        mocker.patch('wpt.utils.check_app_dirs')

        # Mock locking mechanisms
        mock_locking = mocker.patch('msvcrt.locking', create=True) if sys.platform == 'win32' else None
        mock_flock = mocker.patch('fcntl.flock', create=True) if sys.platform != 'win32' else None

        # Should not exit
        ensure_single_instance()

        if sys.platform == 'win32':
            mock_locking.assert_called_once()
        else:
            mock_flock.assert_called_once()

    def test_already_running_failure(self, mocker, capsys):
        import errno

        from wpt.utils import ensure_single_instance

        mocker.patch('os.open', return_value=123)
        mocker.patch('wpt.utils.check_app_dirs')

        # Mock locking to raise IOError (locked)
        error = OSError()
        error.errno = errno.EAGAIN  # Locked

        if sys.platform == 'win32':
            mocker.patch('msvcrt.locking', side_effect=error, create=True)
        else:
            mocker.patch('fcntl.flock', side_effect=error, create=True)

        with pytest.raises(SystemExit) as exc:
            ensure_single_instance()

        assert exc.value.code == errno.ECANCELED
        captured = capsys.readouterr()
        assert 'Another instance of the CLI is already running' in captured.out

    def test_permission_failure(self, mocker, capsys):
        import errno

        from wpt.utils import ensure_single_instance

        # Mock os.open to fail with PermissionError
        mocker.patch('wpt.utils.check_app_dirs')
        mocker.patch('os.open', side_effect=PermissionError('Access Denied'))

        with pytest.raises(SystemExit) as exc:
            ensure_single_instance()

        assert exc.value.code == errno.EPERM
        captured = capsys.readouterr()
        assert 'Could not acquire lock' in captured.out


class TestStatusUtils:
    """Tests for status management functions."""

    def test_check_status_phases_valid(self):
        from wpt.utils import check_status_phases

        # Should not raise
        check_status_phases('i', 'i')
        check_status_phases('u', 'n')

    def test_check_status_phases_invalid(self, capsys):
        import errno

        from wpt.utils import check_status_phases

        with pytest.raises(SystemExit) as exc:
            check_status_phases('x', 'i')
        assert exc.value.code == errno.EINVAL

        with pytest.raises(SystemExit) as exc:
            check_status_phases('i', 'x')
        assert exc.value.code == errno.EINVAL

    def test_update_package_status(self, mocker):
        from wpt.utils import update_package_status

        mocker.patch('wpt.utils.load_status', return_value={})
        mock_write = mocker.patch('wpt.utils.write_status')
        mocker.patch('wpt.utils.os.path.isfile', return_value=True)

        info = update_package_status('pkg', '1.0', 'i', 'i', date='2024-01-01')

        assert info['pkg']['1.0']['status']['desired'] == 'i'
        assert info['pkg']['1.0']['install_date'] == '2024-01-01'
        mock_write.assert_called_once()

    def test_get_package_status_none(self, mocker):
        from wpt.utils import get_package_status

        mocker.patch('wpt.utils.os.path.isfile', return_value=False)
        assert get_package_status('pkg') is None

    def test_get_package_status_found(self, mocker):
        from wpt.utils import get_package_status

        mocker.patch('wpt.utils.os.path.isfile', return_value=True)
        mocker.patch('wpt.utils.load_status', return_value={'pkg': {'data': 1}})
        assert get_package_status('pkg') == {'data': 1}

    def test_get_installed_package_status_success(self, mocker):
        from wpt.utils import get_installed_package_status

        mocker.patch('wpt.utils.os.path.isfile', return_value=True)
        mocker.patch(
            'wpt.utils.load_status', return_value={'pkg': {'1.0': {'status': {'desired': 'i', 'current': 'i'}}}}
        )

        result = get_installed_package_status('pkg')
        assert '1.0' in result

    def test_get_installed_package_status_failures(self, mocker):
        from wpt.utils import get_installed_package_status

        mocker.patch('wpt.utils.os.path.isfile', return_value=True)
        # Case: Package exists but not installed (e.g. removed)
        mocker.patch(
            'wpt.utils.load_status', return_value={'pkg': {'1.0': {'status': {'desired': 'u', 'current': 'n'}}}}
        )
        with pytest.raises(ValueError, match='No installed version'):
            get_installed_package_status('pkg')

        # Case: Package not in status
        mocker.patch('wpt.utils.load_status', return_value={})
        with pytest.raises(ValueError, match='found in status'):
            get_installed_package_status('pkg')

    def test_is_package_installed(self, mocker):
        from wpt.utils import is_package_installed

        mocker.patch('wpt.utils.get_package_status', return_value={'1.0': {'status': {'desired': 'i', 'current': 'i'}}})
        assert is_package_installed('pkg', '1.0') is True

        mocker.patch('wpt.utils.get_package_status', return_value={'1.0': {'status': {'desired': 'u', 'current': 'n'}}})
        assert is_package_installed('pkg', '1.0') is False

        mocker.patch('wpt.utils.get_package_status', return_value=None)
        assert is_package_installed('pkg', '1.0') is False


class TestCreatePackageInfo:
    """Tests for create_package_info function."""

    def test_creates_info(self, mocker, tmp_path):
        from wpt.utils import create_package_info

        # Setup mocks
        mock_copy = mocker.patch('shutil.copy')
        mocker.patch('os.path.isfile', return_value=True)
        mocker.patch('os.path.isdir', return_value=True)

        # Mock os.walk for data directory
        mocker.patch('os.walk', return_value=[('/root', [], ['file1.txt', 'file2.txt'])])
        # Mock file operations for list generation
        mock_open = mocker.patch('builtins.open', mocker.mock_open())

        create_package_info('/src', 'mypkg')

        # Should copy metadata
        assert mock_copy.call_count >= 1
        # Should write file list
        mock_open.assert_called()
