# Command: `wpt import-key`

> **Synopsis:** `wpt import-key <keyfile>`
> **Module:** Repository Management
> **Requires Admin:** No (but GPG keyring may require elevated access)
> **Generated:** 2026-05-20

## Overview

Imports a GPG public key into the system keyring so that WPT can verify repository package index signatures. This is a prerequisite for using `gpg.verify = required` mode.

## Layout

Terminal output only. Prints a warning if import fails and GPG verification is set to `optional`.

## Parameters

| Argument | Required | Description |
|----------|----------|-------------|
| `keyfile` | Yes | Path to the GPG public key file to import |

## Interactions

### Key Import Flow

- **Trigger:** `wpt import-key <keyfile>`
- **Behavior:**
  1. Runs `gpg --import <keyfile>` as a subprocess (list-based, no shell injection).
  2. If import succeeds: returns without output (the CLI prints the version banner unless `--quiet`).
  3. If import fails **and** `[gpg] verify = required` in config: raises `RuntimeError("Failed to import GPG key")` — exits with failure code.
  4. If import fails **and** `[gpg] verify != required`: logs a warning ("Failed to import GPG key (ignored as GPG verification is optional/disabled)") — exits normally.

## Dependencies

Requires the `gpg` binary to be available on the system PATH.

## Business Rules

- The GPG keyring used is the current user's default keyring (managed by `gpg` itself — WPT does not specify a custom keyring).
- `import-key` does not validate that the key file is in a specific format; that validation is delegated entirely to `gpg`.
- If `gpg` is not installed, the import fails with `FileNotFoundError`, which is caught and logged as an error.
- The error severity (fatal vs. warning) is controlled entirely by the `[gpg] verify` configuration setting.
