import contextlib
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


def cleanup_old_files(dir_path: str, suffix: str):
    """Attempt to delete any files ending with the given suffix (e.g., .old)."""
    for root, _dirs, files in os.walk(dir_path, topdown=False):
        for file in files:
            if file.endswith(suffix):
                file_path = os.path.join(root, file)
                with contextlib.suppress(Exception):
                    os.remove(file_path)


def rename_files_recursively(dir_path: str, suffix: str):
    """Recursively rename all files inside dir_path by appending a suffix."""
    for root, _dirs, files in os.walk(dir_path, topdown=False):
        for file in files:
            if not file.endswith(suffix):
                file_path = os.path.join(root, file)
                new_file_path = file_path + suffix
                try:
                    if os.path.exists(new_file_path):
                        os.remove(new_file_path)
                    os.rename(file_path, new_file_path)
                except Exception as e:
                    print(f"Warning: Could not rename file '{file_path}' to '{new_file_path}': {e}", file=sys.stderr)


def copy_tree_contents(src: str, dst: str):
    """Copy directory contents recursively, overwriting existing files."""
    if not os.path.exists(dst):
        os.makedirs(dst)
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            copy_tree_contents(s, d)
        else:
            shutil.copy2(s, d)


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

    # 2. Relocate files
    copied_successfully = False
    if os.path.exists(target_install_dir):
        backup_name = f'wpt.old.{uuid.uuid4().hex[:8]}'
        backup_dir = os.path.join(program_data, backup_name)
        try:
            os.rename(target_install_dir, backup_dir)
            print(f"[+] Active installation backed up to '{backup_name}' to allow hot-swapping.")
            shutil.copytree(wpt_install_dir, target_install_dir)
            copied_successfully = True
        except Exception as rename_err:
            print(f'[*] Folder rename failed ({rename_err}). Falling back to in-place file hot-swapping...')

            # Clean up old .old files from previous fallback runs
            cleanup_old_files(target_install_dir, '.old')

            # Rename all files in-place with .old suffix
            rename_files_recursively(target_install_dir, '.old')

            # Copy contents of new version in place
            try:
                copy_tree_contents(wpt_install_dir, target_install_dir)
                print('[+] Files successfully hot-swapped in place.')
                copied_successfully = True
            except Exception as copy_err:
                print(f'Error relocating files in-place: {copy_err}', file=sys.stderr)
                sys.exit(1)
    else:
        try:
            shutil.copytree(wpt_install_dir, target_install_dir)
            copied_successfully = True
        except Exception as e:
            print(f'Error copying files: {e}', file=sys.stderr)
            sys.exit(1)

    if copied_successfully:
        # Clear the managed cache to save space
        try:
            for item in os.listdir(wpt_install_dir):
                item_path = os.path.join(wpt_install_dir, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            print('[+] Managed cache cleared.')
        except Exception as e:
            print(f'Warning: Error clearing cache: {e}', file=sys.stderr)

    # 4. Register in App Paths
    success_reg = register_in_app_paths(target_exe_path, target_install_dir)
    if not success_reg:
        sys.exit(1)

    print('wpt installation completed successfully.')
    sys.exit(0)


if __name__ == '__main__':
    main()
