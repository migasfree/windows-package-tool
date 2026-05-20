# Command: `wpt download`

> **Synopsis:** `wpt download [-o <dir>] <package>`
> **Module:** Package Authoring
> **Requires Admin:** No
> **Generated:** 2026-05-20

## Overview

Downloads the latest version of a package to disk without installing it. Useful for staging packages for offline distribution, inspection, or manual deployment.

## Layout

Terminal output. Shows a real-time download progress bar (spinner, bar, downloaded bytes, speed, time remaining). On success, prints the path to the downloaded file.

## Parameters

| Argument | Required | Description |
|----------|----------|-------------|
| `package` | Yes | Name of the package to download |
| `-o` / `--output` | No | Destination directory. Defaults to the current working directory. Created if it does not exist. |

## Interactions

### Download Flow

- **Trigger:** `wpt download <package>`
- **Behavior:**
  1. Loads the repository cache. If empty, calls `update_local_repo_info()` to load from disk.
  2. Looks up `<package>` in the cache. Raises `KeyError` if not found.
  3. Selects the latest version (by `packaging.version.parse`, descending sort).
  4. Constructs the download URL: `<repo_url>/<name>_<version>_x64.tar.gz`.
  5. Streams the download to `<output_dir>/<name>_<version>_x64.tar.gz`. Shows progress bar.
  6. Verifies the SHA-256 hash against the repository manifest entry. Raises `ValueError` on mismatch.
  7. Prints the path to the downloaded file.
  8. The output directory is created if it does not exist (`os.makedirs`).

## Dependencies

| Service | URL Pattern | Trigger | Notes |
|---------|-------------|---------|-------|
| Package download | `GET <repo_url>/<name>_<version>_x64.tar.gz` | On command | Streamed |

## Business Rules

- Always downloads the **latest** version available in the repository. There is no version pinning for `download`.
- Hash verification uses SHA-256 (same as `install`). A hash mismatch produces a `ValueError` and the downloaded file is left on disk.
- The command does not require admin privileges and does not modify `status.json` or the registry.
