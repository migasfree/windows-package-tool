import os
import sys
import uuid

APP_PATHS_KEY = r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths'
EXE_NAME = 'wpt.exe'


def remove_from_registry(exe_name: str) -> bool:
    """Removes the executable from the Windows App Paths registry."""
    if sys.platform != 'win32':
        return True

    import winreg

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

    if not success_reg:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
