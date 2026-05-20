# Command: `wpt search`

> **Synopsis:** `wpt search [<query>] [-s]`
> **Module:** Package Discovery
> **Requires Admin:** No
> **Generated:** 2026-05-20

## Overview

Searches the repository catalog for available packages matching a name or description pattern. The search works against the locally cached `packages.json` (not in real time against the server). If the cache is empty, it is loaded automatically.

## Layout

Without `--summary`: Renders a formatted table with Name, Version (latest), Description columns.
With `--summary`: Prints one package name per line, sorted alphabetically.
No results: Prints a yellow warning message.

## Parameters

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `query` | No | `*` | Search string matched as a case-insensitive regex against package name and description. Omitting it or passing `*` returns all packages. |
| `-s` / `--summary` | No | Off | Print compact name-only output |

## Fields

### Table View

| Column | Notes |
|--------|-------|
| Name | Matched package name (cyan) |
| Version | Latest available version in the repository (green) |
| Description | Package description text |

## Interactions

### Search Execution

- **Trigger:** `wpt search <query>`
- **Behavior:**
  1. Loads repository cache. If empty, calls `update_local_repo_info()` to load from disk (not from network — `regenerate=False`).
  2. Compiles the query as a Python `re.compile(query.lower())` pattern. If query is `*` or omitted, uses `re.compile('.*')` (matches everything).
  3. For each package in the catalog, gets the latest version (by string `max()` — **not** by semantic versioning for search purposes [TBC]).
  4. Tests the pattern against `package_name.lower()` and `description.lower()`.
  5. Collects all matching `(name, latest_version, description)` tuples.
  6. If `--summary`: prints names sorted alphabetically.
  7. Otherwise: renders a table sorted by name.
  8. If no results found and not quiet: prints a warning.

## Business Rules

- The query is a **regex pattern**, not a glob or substring match. Users can use regex metacharacters (`.`, `*`, `+`, etc.). A plain string like `notepad` will match any package whose name or description contains "notepad".
- Search matches against **latest version only** of each package in the catalog.
- Search does **not** perform a network request if the cache file already exists on disk.
- The version shown is always the latest available in the repository, not the installed version.
- Deduplication: results are stored in a `set()` — if the same package appeared in multiple repository sources, it appears only once in the output.
