import contextlib
import os
import shutil
import sys
import uuid

if sys.platform == 'win32':
    import ctypes
    import winreg
    from ctypes import wintypes

APP_PATHS_BASE = r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths'
EXE_NAME = 'wpt.exe'


def register_in_app_paths(exe_path: str, install_dir: str) -> bool:
    """Registers the executable in Windows App Paths for global shell execution."""
    if sys.platform != 'win32':
        return True

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


def add_to_system_path(install_dir: str) -> bool:
    """Idempotently adds the installation directory to the system PATH environment variable."""
    if sys.platform != 'win32':
        return True

    env_key_path = r'System\CurrentControlSet\Control\Session Manager\Environment'
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, env_key_path, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            try:
                current_path, value_type = winreg.QueryValueEx(key, 'Path')
            except FileNotFoundError:
                current_path = ''
                value_type = winreg.REG_EXPAND_SZ

            normalized_install_dir = os.path.normpath(install_dir).lower()
            paths = [os.path.normpath(p).lower() for p in current_path.split(';') if p]

            if normalized_install_dir not in paths:
                new_path = current_path
                if new_path and not new_path.endswith(';'):
                    new_path += ';'
                new_path += install_dir

                winreg.SetValueEx(key, 'Path', 0, value_type, new_path)
                print(f"Successfully added '{install_dir}' to the system PATH.")

                # Broadcast environment update to system
                hwnd_broadcast = 0xFFFF
                wm_settingchange = 0x001A
                smto_abortifhung = 0x0002

                result = wintypes.DWORD()
                ctypes.windll.user32.SendMessageTimeoutW(
                    hwnd_broadcast,
                    wm_settingchange,
                    0,
                    'Environment',
                    smto_abortifhung,
                    5000,
                    ctypes.byref(result),
                )
    except PermissionError:
        print(
            'Permission denied: Unable to modify system PATH. Run as Administrator.',
            file=sys.stderr,
        )
        return False
    except Exception as e:
        print(f'Warning: Could not modify system PATH: {e}', file=sys.stderr)
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


def should_ignore(path: str, dir_path: str) -> bool:
    """Check if the given path should be ignored (preserved) during upgrades."""
    ignored_items = {
        'wpt.conf',
        'sources.list',
        'status.json',
        'packages.json',
        'wpt.lock',
        'wpt.log',
        'conf.d',
        'keys',
        'packages',
        'gpg',
        'info',
        'temp',
        'cache',
    }
    try:
        rel_path = os.path.relpath(path, dir_path)
        first_component = rel_path.split(os.sep)[0].lower()
        return first_component in ignored_items
    except Exception:
        return False


def restore_preserved_items(backup_dir: str, target_install_dir: str):
    """Restore user configuration and data files from backup to the new installation directory."""
    preserve_items = [
        'wpt.conf',
        'sources.list',
        'status.json',
        'wpt.lock',
        'wpt.log',
        'conf.d',
        'keys',
        'packages',
        'gpg',
        'info',
        'temp',
        'cache',
    ]

    for item in preserve_items:
        src = os.path.join(backup_dir, item)
        dst = os.path.join(target_install_dir, item)

        if not os.path.exists(src):
            continue

        try:
            if os.path.isdir(src):
                if os.path.exists(dst):
                    # Merge directories
                    for root, _dirs, files in os.walk(src):
                        rel_path = os.path.relpath(root, src)
                        dst_dir = os.path.join(dst, rel_path) if rel_path != '.' else dst
                        os.makedirs(dst_dir, exist_ok=True)
                        for file in files:
                            s_file = os.path.join(root, file)
                            d_file = os.path.join(dst_dir, file)
                            if os.path.exists(d_file):
                                with contextlib.suppress(Exception):
                                    os.remove(d_file)
                            shutil.move(s_file, d_file)
                else:
                    shutil.move(src, dst)
            else:
                if os.path.exists(dst):
                    with contextlib.suppress(Exception):
                        os.remove(dst)
                shutil.move(src, dst)
            print(f"[+] Restored user data item: '{item}'")
        except Exception as e:
            print(f"Warning: Could not restore '{item}' from backup: {e}", file=sys.stderr)


def cleanup_old_files(dir_path: str, suffix: str):
    """Attempt to delete any files ending with the given suffix (e.g., .old), ignoring user data."""
    for root, _dirs, files in os.walk(dir_path, topdown=False):
        for file in files:
            file_path = os.path.join(root, file)
            if should_ignore(file_path, dir_path):
                continue
            if file.endswith(suffix):
                with contextlib.suppress(Exception):
                    os.remove(file_path)


def rename_files_recursively(dir_path: str, suffix: str):
    """Recursively rename all files inside dir_path by appending a suffix, ignoring user data."""
    for root, _dirs, files in os.walk(dir_path, topdown=False):
        for file in files:
            file_path = os.path.join(root, file)
            if should_ignore(file_path, dir_path):
                continue
            if not file.endswith(suffix):
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


def update_pkg_list(target_dir: str) -> None:
    """Regenerate the WPT .list manifest with actual installed paths."""
    pkg_list = os.environ.get('WPT_PKG_LIST')
    if not pkg_list:
        return

    files = []
    for root, _, archives in os.walk(target_dir):
        for item in archives:
            files.append(os.path.join(root, item))

    with open(pkg_list, 'w', encoding='utf-8') as f:
        for path in sorted(files):
            f.write(f'{path}\n')


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
            restore_preserved_items(backup_dir, target_install_dir)
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

    # Update the WPT .list manifest with the actual installed paths
    update_pkg_list(target_install_dir)

    # 4. Register in App Paths
    success_reg = register_in_app_paths(target_exe_path, target_install_dir)
    if not success_reg:
        sys.exit(1)

    # 5. Add to system PATH
    success_path = add_to_system_path(target_install_dir)
    if not success_path:
        sys.exit(1)

    print('wpt installation completed successfully.')
    sys.exit(0)


if __name__ == '__main__':
    main()
