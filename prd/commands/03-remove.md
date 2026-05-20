# Command: `wpt remove`

> **Synopsis:** `wpt remove [-f] <package> [<package2> ...]`
> **Module:** Package Lifecycle
> **Requires Admin:** Yes
> **Generated:** 2026-05-20

## Overview

Removes one or more WPT-managed packages from the system. Checks whether other installed packages depend on the package being removed (unless `--force` is used), prompts for confirmation before removing dependent packages, and runs the package's lifecycle removal scripts in order.

## Layout

Terminal output only. Output includes lists of packages to be removed (if dependencies are affected) and a confirmation prompt.

## Parameters

| Argument | Required | Format | Description |
|----------|----------|--------|-------------|
| `package` | Yes (one or more) | `<name>` | Name of the installed package to remove |
| `-f` / `--force` | No | Flag | Skip dependency checks; force removal regardless of reverse dependencies |

Global flags `-q`, `-y`, `--no-check-certificate`, `--ca-cert` apply.

## Interactions

### Removal Flow

- **Trigger:** User runs `wpt remove <package>`
- **Behavior:**
  1. Validates admin privileges.
  2. Looks up the package in `status.json`. If not installed, raises `ValueError` and exits.
  3. Loads the local repository cache. If unavailable, falls back to reading the locally stored `metadata.json` from `%PROGRAMDATA%\wpt\info\<name>.metadata.json`.
  4. **Dependency check (without `--force`):**
     1. Resolves all transitive dependencies of the package.
     2. Cross-references against currently installed packages.
     3. If other installed packages would become broken, raises `ValueError` listing the conflict.
     4. If dependent packages need to also be removed: lists them and prompts for confirmation (skipped with `-y`). User can cancel.
  5. **Package deconfiguration:**
      1. Sets status to desired `r`, current `i`.
      2. Removes the package entry from the Windows Registry (`HKEY_LOCAL_MACHINE\SOFTWARE\wpt\Packages\<name>`).
      3. Sets status to desired `r`, current `h`.
      4. Executes lifecycle scripts: `prerm`, `remove`, `postrm` (looked up from `%PROGRAMDATA%\wpt\info\`).
      5. Removes individual files listed in `%PROGRAMDATA%\wpt\info\<name>.list`. Files that cannot be deleted are logged as warnings (not fatal).
      6. Removes the package install directory `%PROGRAMDATA%\wpt\packages\<name>\` (recursively).
      7. Deletes all files in `%PROGRAMDATA%\wpt\info\` matching the pattern `<name>.*`.
      8. Sets final status to desired `u`, current `n` with a removal timestamp.

### Force Removal

- **Trigger:** `wpt remove --force <package>`
- **Behavior:** Skips steps 4.1–4.4 (dependency resolution and confirmation). Proceeds directly to deconfiguration. Dependent packages are left in an potentially broken state — this is the caller's responsibility.

### Script Failure

- **Trigger:** A lifecycle removal script exits with non-zero code or times out.
- **Behavior:** Raises `RuntimeError`. The package state may be partially removed. No automatic rollback is performed during removal.

## Dependencies

None. Removal operates entirely on local state (status file, info files, registry).

## Business Rules

- Only packages with desired status `i` and current status `i` are considered "installed" and removable.
- The `--force` flag is primarily intended for use by `upgrade`, which handles the full remove → install cycle.
- If a package's `metadata.json` is not found in the local info directory and not in the repository cache, `remove` raises `ValueError` and exits (cannot deconfigure without metadata).
- File removal follows the `.list` manifest. Files that no longer exist on disk are silently skipped.
