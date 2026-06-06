import os
import sys
import uuid

if sys.platform == 'win32':
    import ctypes
    import winreg
    from ctypes import wintypes

APP_PATHS_KEY = r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths'
EXE_NAME = 'wpt.exe'


def remove_from_registry(exe_name: str) -> bool:
    """Removes the executable from the Windows App Paths registry."""
    if sys.platform != 'win32':
        return True

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, APP_PATHS_KEY, 0, winreg.KEY_ALL_ACCESS) as key:
            try:
                winreg.DeleteKey(key, exe_name)
                print(f"Successfully removed '{exe_name}' from Windows App Paths.")
            except FileNotFoundError:
                print(f"'{exe_name}' was not found in App Paths (or already removed).")
            except PermissionError:
                print(
                    f"Permission denied: Unable to delete '{exe_name}' from App Paths. Run as Administrator.",
                    file=sys.stderr,
                )
                return False
    except Exception as e:
        print(f'Error opening Registry App Paths: {e}', file=sys.stderr)
        return False

    return True


def remove_from_system_path(install_dir: str) -> bool:
    """Idempotently removes the installation directory from the system PATH environment variable."""
    if sys.platform != 'win32':
        return True

    env_key_path = r'System\CurrentControlSet\Control\Session Manager\Environment'
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, env_key_path, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            try:
                current_path, value_type = winreg.QueryValueEx(key, 'Path')
            except FileNotFoundError:
                return True

            normalized_install_dir = os.path.normpath(install_dir).lower()
            paths = [p for p in current_path.split(';') if p]
            new_paths = [p for p in paths if os.path.normpath(p).lower() != normalized_install_dir]

            if len(paths) != len(new_paths):
                new_path_str = ';'.join(new_paths)
                if current_path.endswith(';') and new_path_str and not new_path_str.endswith(';'):
                    new_path_str += ';'

                winreg.SetValueEx(key, 'Path', 0, value_type, new_path_str)
                print(f"Successfully removed '{install_dir}' from the system PATH.")

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


def main():
    success_reg = remove_from_registry(EXE_NAME)

    program_data = os.environ.get('PROGRAMDATA', 'C:\\ProgramData')
    target_install_dir = os.path.join(program_data, 'wpt')

    # We should not completely delete wpt because wpt is currently running!
    # Instead, we rename it to wpt.old.xxx to be deleted later by a future install.
    if os.path.isdir(target_install_dir):
        backup_name = f'wpt.old.{uuid.uuid4().hex[:8]}'
        backup_dir = os.path.join(program_data, backup_name)
        try:
            os.rename(target_install_dir, backup_dir)
            print(f"Successfully marked '{target_install_dir}' for deletion as '{backup_name}'.")
        except Exception as e:
            print(f'Warning: Failed to rename directory {target_install_dir}: {e}', file=sys.stderr)

    success_path = remove_from_system_path(target_install_dir)

    if not success_reg or not success_path:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
