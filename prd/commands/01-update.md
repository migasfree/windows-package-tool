# Command: `wpt update`

> **Synopsis:** `wpt update`
> **Module:** Repository Management
> **Requires Admin:** Yes
> **Generated:** 2026-05-20

## Overview

Reads all configured repository sources, downloads each repository's package index (`packages.json`), optionally verifies its GPG signature, and stores the merged result as a local cache file. This is the prerequisite for any installation or search operation against the remote catalog.

## Layout

This is a non-interactive, terminal-output-only command. Output consists of:

- Printed list of repository URLs being contacted
- A spinner/progress indicator while fetching
- Confirmation of the cache file written
- Any warnings about insecure URLs (HTTP) or signature failures

## Parameters

This command takes no arguments beyond the global flags (`-q`, `-y`, `--no-check-certificate`, `--ca-cert`).

## Interactions

### Command Execution

- **Trigger:** User runs `wpt update`
- **Behavior:**
  1. Checks that `sources.list` exists at `%PROGRAMDATA%\wpt\sources.list`. If missing, raises a `FileNotFoundError` and exits.
  2. Reads all non-comment lines from `sources.list`. Each line has the form `<url> <label>`.
  3. For each URL, downloads `<url>/packages.json` using HTTPS (SSL validation per config/flags).
  4. If the URL uses plain HTTP, logs a warning.
  5. Parses the downloaded JSON. If parsing fails, logs the error and moves to the next source (partial failures do not abort the command).
  6. **GPG verification** (controlled by `[gpg] verify` config):
     - **`required`**: Downloads `<url>/packages.json.sig`. If the file is missing or the signature fails, skips this repository entirely and logs an error.
     - **`optional`** (default): Downloads the `.sig` file; if missing or invalid, logs a warning but continues.
     - **`disabled`**: Skips GPG verification entirely.
  7. Injects the source URL into each package entry's metadata.
  8. Merges all repository data (later sources overwrite earlier ones for the same package name).
  9. Writes the merged result to `%PROGRAMDATA%\wpt\packages.json`.
- **On empty result:** Prints a warning that the repository data is empty and advises checking logs.

### GPG Signature Verification Flow

1. Fetch `packages.json.sig` from the same base URL.
2. Write both files to temporary paths on disk.
3. Run `gpg --verify <sig_path> <json_path>`.
4. Clean up temporary files regardless of outcome.
5. If GPG is not installed, the verification fails silently with a log warning.

## Dependencies

| Service | URL Pattern | Trigger | Notes |
|---------|-------------|---------|-------|
| Package index | `GET <repo_url>/packages.json` | On each source | Parsed as JSON |
| GPG signature | `GET <repo_url>/packages.json.sig` | When GPG mode is not `disabled` | HTTP 404 treated as "no signature available" |

## Business Rules

- Sources with JSON parse errors are silently skipped (logged as `ERROR`); they do not abort the entire update.
- GPG verification requires the `gpg` binary to be available on the system PATH. If not found, verification is treated as failed.
- The local cache (`packages.json`) is a flat merge of all sources. If the same package exists in multiple repos, the last-processed source wins.
- HTTP (non-HTTPS) sources are accepted but logged as warnings. They are not blocked.
