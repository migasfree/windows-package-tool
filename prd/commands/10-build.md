# Command: `wpt build`

> **Synopsis:** `wpt build <directory>`
> **Module:** Package Authoring
> **Requires Admin:** No
> **Generated:** 2026-05-20

## Overview

Creates a distributable WPT package (`.tar.gz` archive) from a source directory. Validates the package structure and metadata before building, computes the SHA-256 hash of the output file, and prints both the output path and hash for inclusion in a repository manifest.

## Layout

Terminal output. On success, prints the output file path (green) and its SHA-256 hash (dim text).

## Parameters

| Argument | Required | Description |
|----------|----------|-------------|
| `directory` | Yes | Path to the package source directory (must contain a `pms/` subdirectory) |

## Required Source Directory Structure

```
<directory>/
├── pms/
│   ├── metadata.json          # Mandatory
│   ├── [preinst.py|ps1|cmd]   # Optional lifecycle scripts
│   ├── [install.py|ps1|cmd]   # Required if data/ exists
│   ├── [postinst.py|ps1|cmd]
│   ├── [prerm.py|ps1|cmd]
│   ├── [remove.py|ps1|cmd]    # Required if data/ exists
│   └── [postrm.py|ps1|cmd]
└── [data/]                    # Optional payload directory
```

## Fields

### `metadata.json` Required Fields

| Field | Required | Validation |
|-------|----------|------------|
| `name` | Yes | Non-empty string |
| `version` | Yes | Non-empty string (PEP 440 recommended) |
| `maintainer` | Yes | Non-empty string |
| `description` | Yes | Non-empty string |
| `specification` | Yes | Must be exactly `"1.0.0"` |
| `dependencies` | No | Must be a list if present; each item must match `<name> (<op> <version>)` format with valid PEP 440 version |
| `homepage` | No | Optional URL string |

## Interactions

### Build Flow

- **Trigger:** `wpt build <directory>`
- **Behavior:**
  1. Verifies that `<directory>/pms/` exists. Raises `ValueError` if missing.
  2. Verifies that `<directory>/pms/metadata.json` exists. Raises `ValueError` if missing.
  3. Reads and validates `metadata.json`:
     - All required fields must be present.
     - `specification` must equal `"1.0.0"`.
     - `dependencies` (if present) must be a list, each entry matching the dependency format.
     - Dependency version strings must be valid PEP 440 versions.
  4. If `<directory>/data/` exists, verifies that **both** an `install` script and a `remove` script exist (with any of `.ps1`, `.cmd`, `.py` extension). Raises `ValueError` if either is missing.
  5. Computes the output filename: `<name>_<version>_x64.tar.gz`.
  6. If the output file already exists in the current directory, deletes it first.
  7. Changes into `<directory>`, archives all its contents (excluding the output file itself) into a `.tar.gz`, then moves the archive to the parent of `<directory>`.
  8. Changes back to the original working directory (guaranteed by `try/finally`).
  9. Computes SHA-256 of the output file.
  10. Prints the final path and hash.

### Output

```txt
Created package file: /path/to/<name>_<version>_x64.tar.gz
Hash: <sha256hex>
```

## Business Rules

- The output file is always placed **one level above** the source directory (sibling of `<directory>`).
- The `x64` architecture suffix is hardcoded — WPT currently only supports 64-bit packages.
- If any validation fails, `ValueError` is raised with a descriptive message and no output file is created.
- The SHA-256 hash output is intended to be pasted into the repository's `packages.json` manifest under the `hash` field.
- Dependency version operators supported: `=`, `>`, `<`, `>=`, `<=`.
