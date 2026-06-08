import importlib.util
import os
import tempfile
from pathlib import Path

# Dynamically import packaging/wpt/pms/install.py
SPEC_PATH = Path(__file__).parent.parent / 'packaging' / 'wpt' / 'pms' / 'install.py'
spec = importlib.util.spec_from_file_location('install_script', str(SPEC_PATH))
install_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(install_module)


def test_should_ignore():
    """Verify that should_ignore correctly flags user data paths to be preserved."""
    dir_path = '/mock/programdata/wpt'

    # User-specific configuration and status paths directly in the root
    assert install_module.should_ignore(os.path.join(dir_path, 'wpt.conf'), dir_path) is True
    assert install_module.should_ignore(os.path.join(dir_path, 'sources.list'), dir_path) is True
    assert install_module.should_ignore(os.path.join(dir_path, 'status.json'), dir_path) is True
    assert install_module.should_ignore(os.path.join(dir_path, 'wpt.lock'), dir_path) is True
    assert install_module.should_ignore(os.path.join(dir_path, 'wpt.log'), dir_path) is True

    # User-specific directories
    assert install_module.should_ignore(os.path.join(dir_path, 'conf.d', 'custom.conf'), dir_path) is True
    assert install_module.should_ignore(os.path.join(dir_path, 'keys', 'repo.gpg'), dir_path) is True
    assert install_module.should_ignore(os.path.join(dir_path, 'packages', 'pkg.tar.gz'), dir_path) is True
    assert install_module.should_ignore(os.path.join(dir_path, 'gpg', 'secring.gpg'), dir_path) is True
    assert install_module.should_ignore(os.path.join(dir_path, 'info', 'pkg.list'), dir_path) is True
    assert install_module.should_ignore(os.path.join(dir_path, 'temp', 'tmpfile'), dir_path) is True
    assert install_module.should_ignore(os.path.join(dir_path, 'cache', 'cached_pkg'), dir_path) is True

    # Application package code and resources that should NOT be ignored (must be upgraded)
    assert install_module.should_ignore(os.path.join(dir_path, 'wpt.exe'), dir_path) is False
    assert install_module.should_ignore(os.path.join(dir_path, 'python.dll'), dir_path) is False
    assert install_module.should_ignore(os.path.join(dir_path, 'conf', 'wpt.conf'), dir_path) is False
    assert install_module.should_ignore(os.path.join(dir_path, 'conf', 'conf.d', 'README'), dir_path) is False


def test_restore_preserved_items():
    """Verify that restore_preserved_items restores user data files and merges directories from backup."""
    with tempfile.TemporaryDirectory() as tmpdir:
        backup_dir = os.path.join(tmpdir, 'backup')
        target_dir = os.path.join(tmpdir, 'target')

        os.makedirs(backup_dir)
        os.makedirs(target_dir)

        # 1. Setup user config/data in the backup folder
        with open(os.path.join(backup_dir, 'wpt.conf'), 'w') as f:
            f.write('user_setting = True')
        with open(os.path.join(backup_dir, 'sources.list'), 'w') as f:
            f.write('http://myrepo.local')
        with open(os.path.join(backup_dir, 'status.json'), 'w') as f:
            f.write('{"packages": []}')

        os.makedirs(os.path.join(backup_dir, 'conf.d'))
        with open(os.path.join(backup_dir, 'conf.d', 'my_custom.conf'), 'w') as f:
            f.write('custom = 1')

        os.makedirs(os.path.join(backup_dir, 'info'))
        with open(os.path.join(backup_dir, 'info', 'package-a.list'), 'w') as f:
            f.write('installed files')

        # 2. Setup the target (new install) directory (which has code and default configs)
        with open(os.path.join(target_dir, 'wpt.exe'), 'w') as f:
            f.write('BINARY_DATA')
        os.makedirs(os.path.join(target_dir, 'conf'))
        with open(os.path.join(target_dir, 'conf', 'wpt.conf'), 'w') as f:
            f.write('default_setting = True')

        # Simulate default configs that might get copied over during install
        # Note: If target has a default wpt.conf, we want it overwritten by user config
        with open(os.path.join(target_dir, 'wpt.conf'), 'w') as f:
            f.write('default_setting = True')

        # 3. Perform restoration
        install_module.restore_preserved_items(backup_dir, target_dir)

        # 4. Assertions
        # Check files are correctly restored
        assert os.path.exists(os.path.join(target_dir, 'wpt.conf'))
        with open(os.path.join(target_dir, 'wpt.conf')) as f:
            assert f.read() == 'user_setting = True'  # Overwritten!

        assert os.path.exists(os.path.join(target_dir, 'sources.list'))
        with open(os.path.join(target_dir, 'sources.list')) as f:
            assert f.read() == 'http://myrepo.local'

        assert os.path.exists(os.path.join(target_dir, 'status.json'))

        assert os.path.exists(os.path.join(target_dir, 'conf.d', 'my_custom.conf'))
        with open(os.path.join(target_dir, 'conf.d', 'my_custom.conf')) as f:
            assert f.read() == 'custom = 1'

        assert os.path.exists(os.path.join(target_dir, 'info', 'package-a.list'))

        # Make sure binaries are untouched
        assert os.path.exists(os.path.join(target_dir, 'wpt.exe'))
        assert os.path.exists(os.path.join(target_dir, 'conf', 'wpt.conf'))


def test_rename_and_cleanup_preserve_user_data():
    """Verify that rename_files_recursively and cleanup_old_files preserve user files in fallback mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create user configuration/data files
        with open(os.path.join(tmpdir, 'wpt.conf'), 'w') as f:
            f.write('config')
        with open(os.path.join(tmpdir, 'status.json'), 'w') as f:
            f.write('status')
        os.makedirs(os.path.join(tmpdir, 'info'))
        with open(os.path.join(tmpdir, 'info', 'package.list'), 'w') as f:
            f.write('package info')

        # Create code files
        with open(os.path.join(tmpdir, 'wpt.exe'), 'w') as f:
            f.write('binary')
        os.makedirs(os.path.join(tmpdir, 'lib'))
        with open(os.path.join(tmpdir, 'lib', 'helper.py'), 'w') as f:
            f.write('helper code')

        # Run rename_files_recursively
        install_module.rename_files_recursively(tmpdir, '.old')

        # Assert user data was NOT renamed to .old
        assert os.path.exists(os.path.join(tmpdir, 'wpt.conf'))
        assert not os.path.exists(os.path.join(tmpdir, 'wpt.conf.old'))
        assert os.path.exists(os.path.join(tmpdir, 'status.json'))
        assert not os.path.exists(os.path.join(tmpdir, 'status.json.old'))
        assert os.path.exists(os.path.join(tmpdir, 'info', 'package.list'))
        assert not os.path.exists(os.path.join(tmpdir, 'info', 'package.list.old'))

        # Assert code files WERE renamed to .old
        assert not os.path.exists(os.path.join(tmpdir, 'wpt.exe'))
        assert os.path.exists(os.path.join(tmpdir, 'wpt.exe.old'))
        assert not os.path.exists(os.path.join(tmpdir, 'lib', 'helper.py'))
        assert os.path.exists(os.path.join(tmpdir, 'lib', 'helper.py.old'))

        # Run cleanup_old_files
        install_module.cleanup_old_files(tmpdir, '.old')

        # Assert that only the code .old files are deleted, user files remain intact
        assert os.path.exists(os.path.join(tmpdir, 'wpt.conf'))
        assert os.path.exists(os.path.join(tmpdir, 'status.json'))
        assert os.path.exists(os.path.join(tmpdir, 'info', 'package.list'))

        assert not os.path.exists(os.path.join(tmpdir, 'wpt.exe.old'))
        assert not os.path.exists(os.path.join(tmpdir, 'lib', 'helper.py.old'))
