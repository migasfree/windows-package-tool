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
        with pytest.raises(ValueError, match='but version 2.0.0 is required'):
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
        with pytest.raises(ValueError, match='must be "1.0.0"'):
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
