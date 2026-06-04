from cx_Freeze import Executable, setup

# Import version from the package
from wpt import __version__

# Dependencies are automatically detected, but they might need fine tuning.
build_exe_options = {
    'packages': ['os', 'wpt', 'rich', 'requests', 'wmi', 'win32com'],
    'excludes': ['tkinter', 'unittest', 'pydoc'],
    'include_files': [
        ('conf/wpt.conf', 'conf/wpt.conf'),
        ('conf/conf.d/README', 'conf/conf.d/README'),
    ],
}

# bdist_msi options for the Windows Installer
bdist_msi_options = {
    'add_to_path': True,
    'initial_target_dir': r'[CommonAppDataFolder]\wpt',
    # cx_Freeze automatically generates an UpgradeCode based on the project name.
}

# base="Console" is used for CLI applications
base = 'Console'

setup(
    name='windows-package-tool',
    version=__version__,
    description='Windows Package Tool',
    options={
        'build_exe': build_exe_options,
        'bdist_msi': bdist_msi_options,
    },
    executables=[
        Executable(
            'wpt/__main__.py',
            target_name='wpt.exe',
            base=base,
        )
    ],
)
