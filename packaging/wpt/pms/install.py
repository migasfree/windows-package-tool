import os
import shutil
import sys
import uuid

APP_PATHS_BASE = r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths'
EXE_NAME = 'wpt.exe'


def register_in_app_paths(exe_path: str, install_dir: str) -> bool:
    """Registers the executable in Windows App Paths for global shell execution."""
    if sys.platform != 'win32':
        return True

    import winreg

    app_paths_key = f'{APP_PATHS_BASE}\\{EXE_NAME}'
    try:
        with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, app_paths_key) as key:
            winreg.SetValueEx(key, '', 0, winreg.REG_SZ, exe_path)
            winreg.SetValueEx(key, 'Path', 0, winreg.REG_SZ, install_dir)
        print(f"Successfully registered '{EXE_NAME}' in Windows App Paths.")
    except PermissionError:
        print(
            f"Permission denied: Unable to register '{EXE_NAME}' in App Paths. Run as Administrator.",
            file=sys.stderr,
        )
        return False
    except Exception as e:
        print(f'Error writing Registry App Paths: {e}', file=sys.stderr)
        return False

    return True


def cleanup_old_installations(program_data_dir: str):
    """Remove any previously left over .old directories."""
    try:
        for item in os.listdir(program_data_dir):
            if item.startswith('wpt.old.'):
                old_path = os.path.join(program_data_dir, item)
                try:
                    if os.path.isdir(old_path):
                        shutil.rmtree(old_path)
                        print(f"Cleaned up old installation backup: '{item}'")
                except Exception as e:
                    print(f"Warning: Could not remove old backup '{old_path}': {e}", file=sys.stderr)
    except Exception as e:
        print(f"Warning: Could not list '{program_data_dir}': {e}", file=sys.stderr)


def main():
    wpt_install_dir = os.environ.get('WPT_INSTALL_DIR')
    if not wpt_install_dir:
        print('Error: WPT_INSTALL_DIR is not set.', file=sys.stderr)
        sys.exit(1)

    program_data = os.environ.get('PROGRAMDATA', 'C:\\ProgramData')
    target_install_dir = os.path.join(program_data, 'wpt')
    target_exe_path = os.path.join(target_install_dir, EXE_NAME)

    print(f"[*] Upgrading wpt in '{target_install_dir}'...")

    # 1. Clean up old backups from previous runs
    cleanup_old_installations(program_data)

    # 2. Rename current installation to avoid "File in Use"
    if os.path.exists(target_install_dir):
        backup_name = f'wpt.old.{uuid.uuid4().hex[:8]}'
        backup_dir = os.path.join(program_data, backup_name)
        try:
            os.rename(target_install_dir, backup_dir)
            print(f"[+] Active installation backed up to '{backup_name}' to allow hot-swapping.")
        except Exception as e:
            print(f'Error renaming current installation: {e}', file=sys.stderr)
            sys.exit(1)

    # 3. Copy the new version in place
    try:
        shutil.copytree(wpt_install_dir, target_install_dir)

        # Clear the managed cache to save space (since files are now in ProgramData)
        for item in os.listdir(wpt_install_dir):
            item_path = os.path.join(wpt_install_dir, item)
            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)

        print('[+] Files successfully relocated and managed cache cleared.')
    except Exception as e:
        print(f'Error relocating files: {e}', file=sys.stderr)
        sys.exit(1)

    # 4. Register in App Paths
    success_reg = register_in_app_paths(target_exe_path, target_install_dir)
    if not success_reg:
        sys.exit(1)

    print('wpt installation completed successfully.')
    sys.exit(0)


if __name__ == '__main__':
    main()
