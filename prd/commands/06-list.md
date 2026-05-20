# Command: `wpt list`

> **Synopsis:** `wpt list [-a] [-s]`
> **Module:** Package Discovery
> **Requires Admin:** No
> **Generated:** 2026-05-20

## Overview

Lists software installed on the system. By default shows only WPT-managed packages. With `--all`, includes all software registered in the Windows Uninstall registry (including packages installed by MSI, NSIS, etc.).

## Layout

Without `--summary`: Renders a formatted table with three columns: Name, Version, Description.
With `--summary`: Prints one line per package in the format `<name>_<version>_x64`.

## Parameters

| Flag | Default | Description |
|------|---------|-------------|
| `-a` / `--all` | Off | Include all Windows-installed software (from `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall`) in addition to WPT-managed packages |
| `-s` / `--summary` | Off | Print compact one-liner per package instead of a formatted table |

## Fields

### Table View (default)

| Column | Source | Notes |
|--------|--------|-------|
| Name | Registry `DisplayName` (all software) or `Name` (WPT packages) | Cyan color |
| Version | Registry `DisplayVersion` or `Version` | Green color |
| Description | Registry `Comments` or `Description` | Plain text |

### Summary View (`-s`)

One line per package: `<name>_<version>_x64`

## Interactions

### List WPT Packages (default)

- **Trigger:** `wpt list`
- **Behavior:**
  1. Queries `HKEY_LOCAL_MACHINE\SOFTWARE\wpt\Packages` in the Windows Registry.
  2. Enumerates all subkeys; each subkey is a WPT-managed package.
  3. Reads `Name`, `Version`, `Description`, `Maintainer`, `Specification`, `Homepage` from each subkey.
  4. Renders a table or summary depending on flags.
  5. If no packages found, raises `ValueError("No packages found")`.

### List All Software (`-a`)

- **Trigger:** `wpt list --all`
- **Behavior:**
  1. Queries `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall`.
  2. Enumerates all subkeys. Entries without a `DisplayName` value are skipped.
  3. Reads `DisplayName`, `DisplayVersion` (defaults `"0.0.0"` if missing), `Comments`, `Publisher`.
  4. Appends the WPT-specific package list (same as default mode) to the result.
  5. Renders the combined list.

## Business Rules

- The `--all` flag reads from the Windows Registry and is therefore Windows-only. On non-Windows systems, only the WPT-specific software list (from `status.json`) is available.
- WPT packages appear in **both** the all-software list (via Registry) and the WPT-only list.
- There is no pagination — all results are printed at once.
- Sort order is registry enumeration order (not alphabetical).
