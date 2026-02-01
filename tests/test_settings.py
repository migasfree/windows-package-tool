import os
from unittest.mock import patch

import pytest

from wpt.settings import PMS, _get_data_path


class TestGetDataPath:
    @pytest.fixture(autouse=True)
    def clean_env(self):
        """Clean relevant environment variables before each test"""
        with patch.dict(os.environ, clear=True):
            yield

    def test_windows_programdata_valid(self):
        """Test with valid absolute PROGRAMDATA on Windows"""
        with patch('sys.platform', 'win32'), patch.dict(os.environ, {'PROGRAMDATA': 'C:\\ProgramData'}), patch(
            'os.path.isabs', return_value=True
        ), patch('os.path.isdir', return_value=True):
            path = _get_data_path()
            assert path == os.path.join('C:\\ProgramData', PMS)

    def test_windows_programdata_invalid_relative(self):
        """Test with relative PROGRAMDATA (should fallback)"""
        with patch('sys.platform', 'win32'), patch.dict(
            os.environ, {'PROGRAMDATA': 'ProgramData', 'LOCALAPPDATA': 'C:\\Users\\Test\\AppData\\Local'}
        ):
            # isabs returns False for 'ProgramData'
            def mock_isabs(path):
                return path.startswith('C:\\')

            with patch('os.path.isabs', side_effect=mock_isabs), patch(
                'os.path.isdir', return_value=True
            ):  # isdir True to prove isabs check takes precedence
                path = _get_data_path()
                # Should fallback to LOCALAPPDATA
                assert path == os.path.join('C:\\Users\\Test\\AppData\\Local', PMS)

    def test_windows_programdata_invalid_nonexistent(self):
        """Test with absolute but nonexistent PROGRAMDATA (should fallback)"""
        with patch('sys.platform', 'win32'), patch.dict(
            os.environ, {'PROGRAMDATA': 'C:\\FakeData', 'LOCALAPPDATA': 'C:\\Users\\Test\\AppData\\Local'}
        ), patch('os.path.isabs', return_value=True), patch('os.path.isdir', return_value=False):
            path = _get_data_path()
            # Should fallback to LOCALAPPDATA
            assert path == os.path.join('C:\\Users\\Test\\AppData\\Local', PMS)

    def test_windows_fallback_to_home(self):
        """Test fallback to home directory when no env vars set"""
        with patch('sys.platform', 'win32'), patch.dict(os.environ, {}), patch(
            'os.path.expanduser', return_value='C:\\Users\\Test'
        ):
            path = _get_data_path()
            assert path == os.path.join('C:\\Users\\Test', f'.{PMS}')

    def test_linux_xgd_data_home_valid(self):
        """Test XDG_DATA_HOME on Linux"""
        with patch('sys.platform', 'linux'), patch.dict(os.environ, {'XDG_DATA_HOME': '/opt/data'}), patch(
            'os.path.isabs', return_value=True
        ):
            path = _get_data_path()
            assert path == os.path.join('/opt/data', PMS)

    def test_linux_default_path(self):
        """Test default Linux path ~/.local/share"""
        with patch('sys.platform', 'linux'), patch.dict(os.environ, {}), patch(
            'os.path.expanduser', return_value='/home/test'
        ):
            path = _get_data_path()
            assert path == os.path.join('/home/test', '.local', 'share', PMS)
