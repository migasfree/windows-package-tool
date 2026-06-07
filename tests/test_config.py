import os
import shutil
import tempfile

import pytest

from wpt.config import Config


class TestConfigOrigins:
    @pytest.fixture
    def temp_config_dir(self):
        # Create a temp directory for configuration files
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_default_origins(self, temp_config_dir):
        # No config files exist, should fall back to defaults
        main_config = os.path.join(temp_config_dir, 'wpt.conf')
        conf_d = os.path.join(temp_config_dir, 'conf.d')

        config = Config(main_config, conf_d)

        # Default keys should have 'default' origin
        assert config.origins[('logging', 'level')] == 'default'
        assert config.origins[('ssl', 'verify')] == 'default'
        assert config.loaded_files == []

    def test_main_config_origins(self, temp_config_dir):
        main_config = os.path.join(temp_config_dir, 'wpt.conf')
        conf_d = os.path.join(temp_config_dir, 'conf.d')

        # Write main config file
        with open(main_config, 'w', encoding='utf-8') as f:
            f.write('[logging]\nlevel = DEBUG\n\n[custom]\nsome_key = value\n')

        config = Config(main_config, conf_d)

        # Modified and new keys should point to main_config path
        assert config.get('logging', 'level') == 'DEBUG'
        assert config.origins[('logging', 'level')] == main_config
        assert config.origins[('custom', 'some_key')] == main_config
        # Unmodified keys should remain 'default'
        assert config.origins[('ssl', 'verify')] == 'default'
        assert config.loaded_files == [main_config]

    def test_conf_d_override_origins(self, temp_config_dir):
        main_config = os.path.join(temp_config_dir, 'wpt.conf')
        conf_d = os.path.join(temp_config_dir, 'conf.d')
        os.makedirs(conf_d)

        # Write main config file
        with open(main_config, 'w', encoding='utf-8') as f:
            f.write('[logging]\nlevel = DEBUG\n')

        # Write override in conf.d
        override_file = os.path.join(conf_d, '01-test.conf')
        with open(override_file, 'w', encoding='utf-8') as f:
            f.write('[logging]\nlevel = WARNING\n[ssl]\nverify = false\n')

        config = Config(main_config, conf_d)

        assert config.get('logging', 'level') == 'WARNING'
        assert config.get('ssl', 'verify') == 'false'
        # Check origins reflect the latest file that overrode them
        assert config.origins[('logging', 'level')] == override_file
        assert config.origins[('ssl', 'verify')] == override_file
        assert config.loaded_files == [main_config, override_file]
