# Command: `wpt info`

> **Synopsis:** `wpt info <package>`
> **Module:** Package Discovery
> **Requires Admin:** No
> **Generated:** 2026-05-20

## Overview

Displays detailed metadata for a specific package — whether installed or only available in the repository. Shows name, version, specification, maintainer, description, and dependency list.

## Layout

Renders a two-column table with bold cyan field names and plain-text values. Table title shows the package name.

## Parameters

| Argument | Required | Description |
|----------|----------|-------------|
| `package` | Yes | Name of the package to inspect |

## Fields

| Field | Description |
|-------|-------------|
| Name | Package identifier |
| Version | Version string |
| Specification | WPT package format version (always `1.0.0` for current packages) |
| Maintainer | `Name <email>` string |
| Description | Human-readable description |
| Dependencies | Comma-separated list of dependency strings, or `None` |

## Interactions

### Info Lookup

- **Trigger:** `wpt info <package>`
- **Behavior:**
  1. Loads the repository cache if not already in memory.
  2. Checks if the package has an installed status entry (via `status.json`). If installed, uses the installed version.
  3. If not installed, looks up the package in the repository cache and selects the latest version (by semantic versioning, descending).
  4. Loads the full metadata via `_get_package_metadata(name, version)`.
  5. Renders the metadata table.
  6. If the package is not found in either the status file or the repository, raises `KeyError` with a "not found" message.

## Business Rules

- `info` shows the **installed** version if the package is installed, otherwise the **latest available** version in the repository.
- Dependencies are shown as raw dependency strings (e.g., `"dep-a (>= 1.2)"`), not resolved to actual versions.
- If metadata retrieval fails entirely (both cache and local info file missing), a `KeyError` or `FileNotFoundError` is raised and re-raised to the CLI error handler.
