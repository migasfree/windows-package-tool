import json
from unittest.mock import MagicMock, patch

import pytest

from wpt.package_manager import PackageManager


@pytest.fixture
def pms():
    p = PackageManager()
    p.config = MagicMock()
    p.config.gpg_verify = 'required'
    p.quiet = True
    return p


class TestGPGCleanup:
    @patch('wpt.package_manager.repository.requests.get')
    @patch('wpt.package_manager.repository.verify_signature')
    @patch('wpt.package_manager.repository.os.unlink')
    @patch('wpt.package_manager.repository.os.path.exists', return_value=True)
    @patch('wpt.package_manager.repository.check_app_dirs')
    def test_gpg_cleanup_on_success(self, mock_check, mock_exists, mock_unlink, mock_verify, mock_get, pms):
        # Mock responses
        mock_repo_resp = MagicMock()
        mock_repo_resp.text = json.dumps({'pkg': {'1.0': {'metadata': {}}}})
        mock_repo_resp.status_code = 200

        mock_sig_resp = MagicMock()
        mock_sig_resp.text = 'signature'
        mock_sig_resp.status_code = 200

        mock_get.side_effect = [mock_repo_resp, mock_sig_resp]
        mock_verify.return_value = True

        pms.get_repository_sources = MagicMock(return_value=['http://test.repo stable main'])

        with patch('builtins.open', MagicMock()), patch('json.dump'):
            pms.update_local_repo_info(regenerate=True)

        # verify_signature called once
        assert mock_verify.called
        # unlink called twice (json and sig)
        assert mock_unlink.call_count == 2

    @patch('wpt.package_manager.repository.requests.get')
    @patch('wpt.package_manager.repository.verify_signature')
    @patch('wpt.package_manager.repository.os.unlink')
    @patch('wpt.package_manager.repository.os.path.exists', return_value=True)
    @patch('wpt.package_manager.repository.check_app_dirs')
    def test_gpg_cleanup_on_failure(self, mock_check, mock_exists, mock_unlink, mock_verify, mock_get, pms):
        # Mock responses
        mock_repo_resp = MagicMock()
        mock_repo_resp.text = json.dumps({'pkg': {'1.0': {'metadata': {}}}})
        mock_repo_resp.status_code = 200

        mock_sig_resp = MagicMock()
        mock_sig_resp.text = 'signature'
        mock_sig_resp.status_code = 200

        mock_get.side_effect = [mock_repo_resp, mock_sig_resp]
        mock_verify.return_value = False  # Verification fails

        pms.get_repository_sources = MagicMock(return_value=['http://test.repo stable main'])

        with patch('builtins.open', MagicMock()), patch('json.dump'):
            pms.update_local_repo_info(regenerate=True)

        # verify_signature called once
        assert mock_verify.called
        # unlink should still be called twice
        assert mock_unlink.call_count == 2

    @patch('wpt.package_manager.repository.requests.get')
    @patch('wpt.package_manager.repository.verify_signature')
    @patch('wpt.package_manager.repository.os.unlink')
    @patch('wpt.package_manager.repository.os.path.exists', return_value=True)
    @patch('wpt.package_manager.repository.check_app_dirs')
    def test_gpg_cleanup_on_exception(self, mock_check, mock_exists, mock_unlink, mock_verify, mock_get, pms):
        # Mock responses
        mock_repo_resp = MagicMock()
        mock_repo_resp.text = json.dumps({'pkg': {'1.0': {'metadata': {}}}})
        mock_repo_resp.status_code = 200

        mock_sig_resp = MagicMock()
        mock_sig_resp.text = 'signature'
        mock_sig_resp.status_code = 200

        mock_get.side_effect = [mock_repo_resp, mock_sig_resp]
        mock_verify.side_effect = Exception('Unexpected error')

        pms.get_repository_sources = MagicMock(return_value=['http://test.repo stable main'])

        with patch('builtins.open', MagicMock()), patch('json.dump'), pytest.raises(
            Exception, match='Unexpected error'
        ):
            pms.update_local_repo_info(regenerate=True)

        # unlink should be called even if verify_signature raised an exception
        assert mock_unlink.call_count == 2
