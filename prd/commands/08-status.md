# Command: `wpt status`

> **Synopsis:** `wpt status [-i] <package>`
> **Module:** Package Discovery
> **Requires Admin:** No
> **Generated:** 2026-05-20

## Overview

Displays the installation status of a specific package, including its desired state, current state, and install/remove timestamps. Optionally can be used in scripting mode to return only an exit code indicating whether the package is installed.

## Layout

Terminal output only (unless `-i` is used for scripting). Output is a series of labeled key-value lines: package metadata fields, desired status, current status, and dates if available.

## Parameters

| Argument | Required | Description |
|----------|----------|-------------|
| `package` | Yes | Name of the package to check |
| `-i` / `--is-installed` | No | Silent mode: exit with code `0` if installed, `ENODATA` if not. No text output. |

## Fields

### Status Output

| Field | Description |
|-------|-------------|
| Package metadata fields | All fields from `metadata.json` (name, version, description, maintainer, etc.) |
| Desired Status | Status code and its human-readable label (e.g., `(i) marked for installation`) |
| Current Status | Status code and its human-readable label (e.g., `(i) successfully installed`) |
| Install Date | ISO timestamp of when the package was installed (if available) |
| Remove Date | ISO timestamp of when the package was removed (if available) |

## Interactions

### Status Lookup (normal mode)

- **Trigger:** `wpt status <package>`
- **Behavior:**
  1. Looks up the package in `status.json`.
  2. If found **and** the package is currently installed (desired `i`, current `i`): loads and displays metadata, then shows the desired and current status codes with their labels and any stored dates.
  3. If not installed but has a history entry: loads the raw status entry and displays the historical state (including desired `r`, current `n` for removed packages).
  4. If the package has never appeared in `status.json`: prints a yellow message stating it has never been installed or removed, then exits with `ENODATA`.
  5. Metadata display attempts to load from the repository cache; falls back to the local info file.

### Scripting Mode (`-i`)

- **Trigger:** `wpt status --is-installed <package>`
- **Behavior:**
  - If installed: exits with code `0` (no output).
  - If not installed: exits with `ENODATA` (no output).
  - Used by `migasfree-client` and automation scripts to check package presence without parsing text output.

## Business Rules

- "Installed" means **both** desired = `i` **and** current = `i`. A package marked for installation but not yet configured is not considered installed.
- The `--is-installed` flag is explicitly designed for scripting; it produces no console output.
- If a package has been removed, `status` still shows its last known status (with desired `u`, current `n`) — it does not raise an error.
