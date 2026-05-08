import errno
import sys
from unittest.mock import call, patch

import pytest

from wpt.__main__ import main


@pytest.fixture
def mock_pm(mocker):
    return mocker.patch('wpt.__main__.PackageManager')


@pytest.fixture
def mock_is_admin(mocker):
    return mocker.patch('wpt.__main__.is_admin', return_value=True)


@pytest.fixture
def mock_ensure_single_instance(mocker):
    return mocker.patch('wpt.__main__.ensure_single_instance')


class TestArgParsing:
    def test_no_args_prints_help(self, mocker, mock_ensure_single_instance):
        mocker.patch('sys.exit')

        with patch('sys.stdout'):
            main([])

        sys.exit.assert_called()

    def test_version_print(self, mock_pm, mock_is_admin, mock_ensure_single_instance, capsys):
        # By default not quiet, should print version
        main(['list'])
        captured = capsys.readouterr()
        assert 'Windows Package Tool' in captured.out

    def test_quiet_no_version(self, mock_pm, mock_is_admin, mock_ensure_single_instance, capsys):
        main(['-q', 'list'])
        captured = capsys.readouterr()
        assert 'Windows Package Tool' not in captured.out


class TestAdminCheck:
    @pytest.mark.parametrize('command', ['install', 'remove', 'update', 'upgrade', 'clean'])
    def test_commands_require_admin(self, command, mock_pm, mock_ensure_single_instance, mocker, capsys):
        mocker.patch('wpt.__main__.is_admin', return_value=False)
        mocker.patch('sys.exit')

        args = [command]
        if command in ['install', 'remove']:
            args.append('pkg')

        main(args)

        captured = capsys.readouterr()
        assert 'administrator privileges' in captured.out
        sys.exit.assert_called_with(errno.EPERM)

    @pytest.mark.parametrize('command', ['list', 'search', 'status', 'build', 'info', 'download'])
    def test_commands_no_require_admin(self, command, mock_pm, mock_ensure_single_instance, mocker):
        mocker.patch('wpt.__main__.is_admin', return_value=False)
        # Should not exit
        args = [command]
        if command == 'search':
            args.append('query')
        if command in ['status', 'info', 'download']:
            args.append('pkg')
        if command == 'build':
            args.append('dir')

        main(args)
        # Mock PM should be called
        mock_pm.assert_called()


class TestCommandDispatch:
    def test_install_package(self, mock_pm, mock_is_admin, mock_ensure_single_instance):
        main(['install', 'pkg1', 'pkg2=1.0'])
        instance = mock_pm.return_value
        assert instance.install_package.call_count == 2
        instance.install_package.assert_has_calls([call('pkg1'), call('pkg2', '1.0')])

    def test_remove_package(self, mock_pm, mock_is_admin, mock_ensure_single_instance):
        main(['remove', 'pkg', '-f'])
        instance = mock_pm.return_value
        instance.remove_package.assert_called_with('pkg', True)

    def test_list_packages(self, mock_pm, mock_is_admin, mock_ensure_single_instance):
        main(['list', '-a', '-s'])
        instance = mock_pm.return_value
        instance.list_installed_packages.assert_called_with(True, True)

    def test_search_packages(self, mock_pm, mock_is_admin, mock_ensure_single_instance):
        main(['search', 'query', '-s'])
        instance = mock_pm.return_value
        instance.search_packages.assert_called_with('query', True)

    def test_update(self, mock_pm, mock_is_admin, mock_ensure_single_instance):
        main(['update'])
        instance = mock_pm.return_value
        instance.update_local_repo_info.assert_called_with(regenerate=True)

    def test_upgrade(self, mock_pm, mock_is_admin, mock_ensure_single_instance):
        main(['upgrade'])
        instance = mock_pm.return_value
        instance.upgrade.assert_called()

    def test_status(self, mock_pm, mock_is_admin, mock_ensure_single_instance):
        main(['status', 'pkg', '-i'])
        instance = mock_pm.return_value
        instance.status.assert_called_with('pkg', True)

    def test_clean(self, mock_pm, mock_is_admin, mock_ensure_single_instance):
        main(['clean'])
        instance = mock_pm.return_value
        instance.clean.assert_called()

    def test_build(self, mock_pm, mock_is_admin, mock_ensure_single_instance):
        main(['build', 'dir'])
        instance = mock_pm.return_value
        instance.build.assert_called_with('dir')

    def test_info(self, mock_pm, mock_is_admin, mock_ensure_single_instance):
        main(['info', 'pkg'])
        instance = mock_pm.return_value
        instance.show_info.assert_called_with('pkg')

    def test_download(self, mock_pm, mock_is_admin, mock_ensure_single_instance):
        main(['download', 'pkg', '-o', '/tmp'])
        instance = mock_pm.return_value
        instance.download.assert_called_with('pkg', '/tmp')

    def test_ssl_options(self, mock_pm, mock_is_admin, mock_ensure_single_instance):
        main(['--no-check-certificate', 'list'])
        mock_pm.assert_called_with(False, False, verify=False)

        main(['--ca-cert', '/path/cert', 'list'])
        mock_pm.assert_called_with(False, False, verify='/path/cert')

    @patch('wpt.gpg.import_key')
    def test_import_key_success(self, mock_import, mock_pm, mock_is_admin, mock_ensure_single_instance):
        mock_import.return_value = True
        main(['import-key', 'keyfile'])
        mock_import.assert_called_with('keyfile')

    @patch('wpt.gpg.import_key')
    def test_import_key_failed_required(self, mock_import, mock_pm, mock_is_admin, mock_ensure_single_instance, mocker):
        mock_import.return_value = False
        instance = mock_pm.return_value
        instance.config.gpg_verify = 'required'
        mocker.patch('sys.exit')

        main(['import-key', 'keyfile'])
        sys.exit.assert_called_with(1)

    @patch('wpt.gpg.import_key')
    def test_import_key_failed_optional(self, mock_import, mock_pm, mock_is_admin, mock_ensure_single_instance, mocker):
        mock_import.return_value = False
        instance = mock_pm.return_value
        instance.config.gpg_verify = 'optional'
        mocker.patch('sys.exit')

        main(['import-key', 'keyfile'])
        sys.exit.assert_not_called()


class TestExceptionHandling:
    def test_file_not_found_error(self, mock_pm, mock_is_admin, mock_ensure_single_instance, mocker):
        instance = mock_pm.return_value
        instance.install_package.side_effect = FileNotFoundError('Missing')
        mocker.patch('sys.exit')

        main(['install', 'pkg'])
        sys.exit.assert_called_with(errno.ENOENT)

    def test_key_error(self, mock_pm, mock_is_admin, mock_ensure_single_instance, mocker):
        instance = mock_pm.return_value
        instance.install_package.side_effect = KeyError('Missing')
        mocker.patch('sys.exit')

        main(['install', 'pkg'])
        sys.exit.assert_called_with(errno.ENOENT)

    def test_runtime_error_cancelled(self, mock_pm, mock_is_admin, mock_ensure_single_instance, mocker):
        instance = mock_pm.return_value
        instance.install_package.side_effect = RuntimeError('Cancelled by user')
        mocker.patch('sys.exit')

        main(['install', 'pkg'])
        sys.exit.assert_called_with(errno.ECANCELED)

    def test_generic_error(self, mock_pm, mock_is_admin, mock_ensure_single_instance, mocker):
        instance = mock_pm.return_value
        instance.install_package.side_effect = ValueError('Generic error')
        mocker.patch('sys.exit')

        main(['install', 'pkg'])
        sys.exit.assert_called_with(1)

    def test_request_exception(self, mock_pm, mock_is_admin, mock_ensure_single_instance, mocker, capsys):
        import requests

        instance = mock_pm.return_value
        instance.install_package.side_effect = requests.exceptions.SSLError('SSL verification failed')
        mocker.patch('sys.exit')

        main(['install', 'pkg'])
        sys.exit.assert_called_with(1)
        captured = capsys.readouterr()
        assert 'Connection error' in captured.out
        assert 'bypass SSL validation' in captured.out
