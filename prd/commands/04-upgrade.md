# Command: `wpt upgrade`

> **Synopsis:** `wpt upgrade`
> **Module:** Package Lifecycle
> **Requires Admin:** Yes
> **Generated:** 2026-05-20

## Overview

Compares all currently installed WPT-managed packages against the repository catalog and upgrades any package for which a newer version is available. Each outdated package is first forcefully removed and then reinstalled at the latest version.

## Layout

Terminal output only. No interactive prompts are shown per-package during the upgrade cycle; dependency prompts during individual `install` calls are suppressed by the upgrade flow.

## Parameters

No command-specific arguments. Global flags apply.

## Interactions

### Upgrade Flow

- **Trigger:** User runs `wpt upgrade`
- **Behavior:**
  1. Validates admin privileges.
  2. Reads the list of all currently installed packages from `status.json` (desired `i`, current `i`).
  3. Loads the repository cache. If empty, runs `update` automatically.
  4. For each installed package:
     a. Checks if the package exists in the repository.
     b. Identifies the latest available version (by `packaging.version` comparison — PEP 440 semantics).
     c. If the latest repository version is strictly newer than the installed version, proceeds with upgrade.
     d. Calls `remove --force <package>` (skips dependency checks).
     e. Calls `install <package>` (installs the latest version).
  5. Returns a summary of upgraded packages (`{name: new_version}`).

## Dependencies

Internally composes `remove` and `install`. See those command docs for details.

## Business Rules

- Version comparison uses PEP 440 semantics (via the `packaging` library). Non-PEP-440 version strings may behave unexpectedly.
- Packages not present in the current repository are silently skipped (not an error — they may have been removed from the catalog).
- The upgrade is non-atomic across packages. If upgrading package B fails after A succeeded, A remains at its new version.
- No downgrade protection: if a package was pinned manually at a higher version than what the repo reports, the upgrade command would install a lower version. [TBC — the current code always upgrades to `max()` from repo, so a "downgrade" scenario only occurs if the repo itself removes a newer version.]
