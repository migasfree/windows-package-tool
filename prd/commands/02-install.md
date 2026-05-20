# Command: `wpt install`

> **Synopsis:** `wpt install <package>[=<version>] [<package2>[=<version2>] ...]`
> **Module:** Package Lifecycle
> **Requires Admin:** Yes
> **Generated:** 2026-05-20

## Overview

Downloads, extracts, and configures one or more packages from the repository. Handles dependency resolution recursively, detects circular dependencies, prompts for confirmation before installing additional dependencies, and performs a complete rollback if any lifecycle script fails.

## Layout

Terminal output only. Progress is shown during download (progress bar with speed, ETA, and downloaded bytes). Status messages use color-coded output (green = success, yellow = warning, red = error).

## Parameters

| Argument | Required | Format | Description |
|----------|----------|--------|-------------|
| `package` | Yes (one or more) | `<name>` or `<name>=<version>` | Package name, optionally pinned to an exact version. Multiple packages can be listed. |

Global flags `-q`, `-y`, `--no-check-certificate`, `--ca-cert` apply.

## Fields

### Version Pinning Syntax

| Format | Example | Meaning |
|--------|---------|---------|
| `<name>` | `wpt install notepad-plus` | Install the latest available version |
| `<name>=<version>` | `wpt install notepad-plus=8.6.2` | Install exactly version `8.6.2` |

## Interactions

### Installation Flow

- **Trigger:** User runs `wpt install <package>`
- **Behavior:**
  1. Validates admin privileges (exits with code `5` if not elevated).
  2. Loads local repository cache. If cache is empty, runs `update` automatically.
  3. Reads the current list of installed packages from `status.json`.
  4. Looks up `<package>` in the cache. Raises `KeyError` if not found.
  5. Sets package desired status to `i`, current status to `n` (not installed).
  6. **Download:** Downloads the package `.tar.gz` file from the repository URL. Shows a real-time progress bar (speed, ETA, file size if `Content-Length` header present).
  7. **Hash verification:** Verifies the downloaded file's SHA-256 hash against the repository manifest. Raises `ValueError` on mismatch — the file is not installed.
  8. Updates status to `u` (unpacked).
  9. **Dependency resolution:** Traverses the dependency tree iteratively (not recursively — avoids stack overflow on deep chains). Detects circular dependencies and raises `ValueError` if found.
  10. **Dependency installation (interactive):** If `-y` is not set, lists all additional packages that will be installed and prompts for confirmation. User can cancel.
  11. Installs all dependencies first (recursively calling `install_package`).
  12. **Package configuration:**
      1. Copies `metadata.json` and all lifecycle scripts to `%PROGRAMDATA%\wpt\info\`.
      2. If the package has a `data/` directory, copies all files to `%PROGRAMDATA%\wpt\packages\<name>\`. If the directory already exists, it is deleted first.
      3. Sets status to desired `i`, current `h` (partially installed).
      4. Executes lifecycle scripts in order: `preinst`, `install`, `postinst`.
  13. Writes package metadata to the Windows Registry under `HKEY_LOCAL_MACHINE\SOFTWARE\wpt\Packages\<name>`.
  14. Sets final status to desired `i`, current `i` with the install timestamp.
  15. Cleans up temporary extracted files and the downloaded `.tar.gz`.

### Rollback on Script Failure

- **Trigger:** Any lifecycle script (`preinst`, `install`, `postinst`) exits with a non-zero code or times out.
- **Behavior:**
  1. Deletes the managed files directory (`%PROGRAMDATA%\wpt\packages\<name>\`).
  2. Deletes all metadata files copied to `%PROGRAMDATA%\wpt\info\` for this package.
  3. Reverts status to desired `u`, current `n` (not installed).
  4. Raises `RuntimeError` with a "rolled back" message.

### Script Execution Details

Scripts can be written in Python (`.py`), PowerShell (`.ps1`), or Batch (`.cmd`). The runner:

- Selects the script by trying each extension in order: `.py`, `.cmd`, `.ps1`.
- Enforces a maximum script size of 1 MB.
- Validates the path has no `..` segments (path traversal prevention).
- Sets the `WPT_INSTALL_DIR` environment variable to the package's install directory.
- Runs PowerShell with `-ExecutionPolicy RemoteSigned` to prevent unsigned remote scripts.
- Enforces a configurable timeout (default: 300 seconds).
- Captures stdout and stderr; prints stdout to the console.

### Local Package Installation

- **Trigger:** `wpt install <path/to/package.tar.gz>` (package argument contains a `/` or the file exists on disk).
- **Behavior:** Copies the local file to the temp directory, extracts it, and proceeds with the normal installation flow. Repository cache is not required.

## Dependencies

| Service | URL Pattern | Trigger | Notes |
|---------|-------------|---------|-------|
| Package download | `GET <repo_url>/<name>_<version>_x64.tar.gz` | On install | Streamed in 8 KB chunks |

## Business Rules

- A package already installed at the requested version is **not** re-installed (checked via `status.json`).
- Installing from a `.tar.gz` file directly (local path) bypasses repository lookup.
- Script timeout is configurable via `[scripts] timeout` in `wpt.conf` (default: 300 seconds).
- If a package has a `data/` directory, it **must** also have both `install` and `remove` scripts (one of `.ps1`, `.cmd`, or `.py`). Otherwise, `wpt build` will refuse to create the package.
- Circular dependencies are detected at resolution time and produce an immediate `ValueError`.
