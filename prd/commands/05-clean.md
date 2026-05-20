# Command: `wpt clean`

> **Synopsis:** `wpt clean`
> **Module:** Package Lifecycle
> **Requires Admin:** Yes
> **Generated:** 2026-05-20

## Overview

Removes temporary working files accumulated by previous install/download operations and deletes the local repository cache, freeing disk space and forcing a fresh `update` on the next install or search.

## Layout

Terminal output only. Prints the paths cleaned.

## Parameters

No arguments. Global flags apply.

## Interactions

### Clean Flow

- **Trigger:** User runs `wpt clean`
- **Behavior:**
  1. Validates admin privileges.
  2. Deletes the temp directory (`%PROGRAMDATA%\wpt\temp\`) and immediately recreates it as an empty directory.
  3. Prints confirmation with the temp path.
  4. Deletes the local repository cache file (`%PROGRAMDATA%\wpt\packages.json`) if it exists.
  5. Prints confirmation that the cache file was removed.

## Business Rules

- Installed package metadata (`%PROGRAMDATA%\wpt\info\`) is **not** touched. Only temp files and the repo cache are removed.
- After `clean`, the next `install` or `search` will trigger an automatic `update` to rebuild the cache.
- `clean` does not affect `status.json` (the install/remove history is preserved).
