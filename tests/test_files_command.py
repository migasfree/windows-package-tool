import os
import tempfile

import pytest

from wpt.package_manager import PackageManager


@pytest.fixture
def pms(mocker):
    """PackageManager with heavy dependencies mocked."""
    mocker.patch('wpt.utils.ensure_single_instance')
    mocker.patch('wpt.utils.check_app_dirs')
    return PackageManager(quiet=True)


class TestListPackageFiles:
    def test_not_installed_raises(self, pms, mocker):
        """Should raise ValueError if the package is not installed."""
        mocker.patch(
            'wpt.package_manager.query.get_installed_package_status',
            side_effect=ValueError('not installed'),
        )
        with pytest.raises(ValueError, match='not installed'):
            pms.list_package_files('missing-pkg')

    def test_no_list_file_silent(self, pms, mocker, capsys):
        """Should exit silently when no .list manifest exists (metapackage)."""
        mocker.patch(
            'wpt.package_manager.query.get_installed_package_status',
            return_value={'1.0.0': {'status': {'desired': 'i', 'current': 'i'}}},
        )
        mocker.patch('wpt.package_manager.query.os.path.isfile', return_value=False)

        pms.list_package_files('meta-pkg')
        captured = capsys.readouterr()
        assert captured.out == ''

    def test_prints_files_from_manifest(self, pms, mocker):
        """Should print each absolute path from the .list manifest file."""
        mocker.patch(
            'wpt.package_manager.query.get_installed_package_status',
            return_value={'1.0.0': {'status': {'desired': 'i', 'current': 'i'}}},
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.list', delete=False) as f:
            f.write('C:\\ProgramData\\wpt\\packages\\tool\\bin\\tool.exe\n')
            f.write('C:\\ProgramData\\wpt\\packages\\tool\\lib\\helper.dll\n')
            f.write('\n')  # Blank line — should be ignored
            f.write('C:\\ProgramData\\wpt\\packages\\tool\\README.txt\n')
            list_path = f.name

        try:
            mocker.patch('wpt.package_manager.query.os.path.isfile', return_value=True)
            mocker.patch('wpt.package_manager.query.os.path.join', return_value=list_path)

            output_lines = []
            pms.console.print = lambda msg: output_lines.append(msg)

            pms.list_package_files('tool')

            assert 'C:\\ProgramData\\wpt\\packages\\tool\\bin\\tool.exe' in output_lines
            assert 'C:\\ProgramData\\wpt\\packages\\tool\\lib\\helper.dll' in output_lines
            assert 'C:\\ProgramData\\wpt\\packages\\tool\\README.txt' in output_lines
            # Blank line must be skipped
            assert '' not in output_lines
        finally:
            os.unlink(list_path)

    def test_empty_list_file_silent(self, pms, mocker, capsys):
        """Should produce no output if the .list file exists but is empty."""
        mocker.patch(
            'wpt.package_manager.query.get_installed_package_status',
            return_value={'1.0.0': {'status': {'desired': 'i', 'current': 'i'}}},
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.list', delete=False) as f:
            f.write('')  # Empty
            list_path = f.name

        try:
            mocker.patch('wpt.package_manager.query.os.path.isfile', return_value=True)
            mocker.patch('wpt.package_manager.query.os.path.join', return_value=list_path)

            output_lines = []
            pms.console.print = lambda msg: output_lines.append(msg)

            pms.list_package_files('empty-pkg')
            assert output_lines == []
        finally:
            os.unlink(list_path)
