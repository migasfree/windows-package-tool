# Windows Package Tool (wpt) — Product Requirements Document

> **Generated:** 2026-05-20
> **Version:** 1.0
> **Source:** Reverse-engineered from codebase at `windows-package-tool`

---

## System Overview

**Windows Package Tool (wpt)** is a command-line package management system designed for Windows environments, built to integrate natively with the Migasfree Systems Management ecosystem. It provides system administrators and managed-software pipelines with the same package lifecycle experience that Linux administrators enjoy with APT or DNF — on Windows.

The tool manages a custom package format (`.tar.gz` archives) that includes both application payload files and lifecycle scripts (pre/post install, pre/post remove). Packages are fetched from configurable HTTP/HTTPS repositories, verified via SHA-256 hash, and optionally authenticated via GPG signatures. On installation, package metadata is written to the Windows Registry to make WPT-managed software visible to the OS.

The primary consumers of WPT are `migasfree-client` (which calls WPT as its Windows PMS backend) and system administrators who need to distribute custom tooling to Windows fleets without relying on commercial software distribution platforms.

---

## Module Overview

| Module | Commands | Core Functionality |
|--------|----------|--------------------|
| **Repository Management** | `update`, `import-key` | Fetch remote package indexes, verify GPG signatures, manage local cache |
| **Package Lifecycle** | `install`, `remove`, `upgrade`, `clean` | Full CRUD for managed packages including dependency resolution and rollback |
| **Package Discovery** | `list`, `search`, `status`, `info`, `files` | Query installed and available packages from local state and registry |
| **Package Authoring** | `build`, `download` | Create distributable packages from a source directory; download without installing |
| **Configuration** | `config`, `wpt.conf`, `conf.d/` | INI-based configuration with layered overrides, including active configuration diagnostic tool |

---

## Command Inventory

| # | Command | Synopsis | Module | Doc Link |
|---|---------|----------|--------|----------|
| 1 | `update` | Read online repos, regenerate local cache | Repository Management | [→](./commands/01-update.md) |
| 2 | `install` | Install one or more packages (with version pinning) | Package Lifecycle | [→](./commands/02-install.md) |
| 3 | `remove` | Remove one or more packages (with dependency checks) | Package Lifecycle | [→](./commands/03-remove.md) |
| 4 | `upgrade` | Upgrade all installed packages to latest available | Package Lifecycle | [→](./commands/04-upgrade.md) |
| 5 | `clean` | Delete temp files and local repo cache | Package Lifecycle | [→](./commands/05-clean.md) |
| 6 | `list` | List WPT-managed or all installed software | Package Discovery | [→](./commands/06-list.md) |
| 7 | `search` | Search available packages by name or description | Package Discovery | [→](./commands/07-search.md) |
| 8 | `status` | Show install/remove status of a specific package | Package Discovery | [→](./commands/08-status.md) |
| 9 | `info` | Show detailed metadata for a package | Package Discovery | [→](./commands/09-info.md) |
| 10 | `files` | List all files installed by a package | Package Discovery | [→](./commands/14-files.md) |
| 11 | `build` | Create a `.tar.gz` package from a source directory | Package Authoring | [→](./commands/10-build.md) |
| 12 | `download` | Download a package file without installing it | Package Authoring | [→](./commands/11-download.md) |
| 13 | `import-key` | Import a GPG public key into the system keyring | Repository Management | [→](./commands/12-import-key.md) |
| 14 | `config` | Show configuration information, loaded files, and origins | Configuration | [→](./commands/13-config.md) |

---

## Global Notes

### Permission Model

Commands that modify system state (`install`, `remove`, `update`, `upgrade`, `clean`) require **administrator privileges** on Windows. The tool checks `ctypes.windll.shell32.IsUserAnAdmin()` at startup for these commands and exits with `ERROR_ACCESS_DENIED` (exit code `5`) if not elevated. Read-only commands (`list`, `search`, `status`, `info`, `build`, `download`) do not require elevation.

### Single-Instance Enforcement

Only one WPT process may run at a time. A platform-specific file lock is acquired on `%PROGRAMDATA%\wpt\wpt.lock` at startup. If the lock cannot be acquired (another instance is running), the tool exits immediately with a clear error message.

### Global CLI Flags

| Flag | Effect |
|------|--------|
| `-q` / `--quiet` | Suppresses all output except errors. Used by automated pipelines (e.g., `migasfree-client`). |
| `-d` / `--debug` | Enables verbose debug output directly to the console with detailed logger formatting. |
| `-y` / `--assume-yes` | Auto-confirms all interactive prompts (dependency install/remove confirmations). |
| `--no-check-certificate` | Disables SSL certificate validation for all HTTP requests. |
| `--ca-cert <path>` | Path to a custom CA bundle for certificate verification. Takes precedence over `wpt.conf`. |

### Configuration System

Configuration uses a **layered INI model**:

1. Hardcoded defaults (in code)
2. Main config file: `%PROGRAMDATA%\wpt\wpt.conf`
3. Drop-in overrides: `%PROGRAMDATA%\wpt\conf.d\*.conf` (loaded alphabetically)

Later layers override earlier ones. If `wpt.conf` does not exist, it is automatically copied from the package's bundled template on first run.

### Repository Source Format

The file `%PROGRAMDATA%\wpt\sources.list` lists repository URLs, one per line. Lines beginning with `#` are ignored. Each active line must follow the format: `<url> <label>`. HTTP (non-HTTPS) sources produce a warning in the log.

### Package Status State Machine

Each package tracks two independent status dimensions:

| Dimension | Code | Meaning |
|-----------|------|---------|
| **Desired** | `u` | Unknown |
| **Desired** | `i` | Marked for installation |
| **Desired** | `r` | Marked for removal |
| **Current** | `n` | Not installed |
| **Current** | `i` | Successfully installed |
| **Current** | `u` | Unpacked (extraction complete, scripts pending) |
| **Current** | `h` | Partially installed (scripts in progress) |

### Common Interaction Patterns

- All commands that write packages or metadata require administrator rights.
- `install` automatically calls `update` internally if the local repo cache is empty.
- `upgrade` calls `remove` (force) then `install` for each outdated package.
- All destructive operations (remove, overwrite) that affect dependencies ask for confirmation unless `-y` is set.
- Script failures during `install` trigger a full rollback: managed files are deleted, metadata is removed, and status reverts to `not installed`.

---

## Exit Code Reference

| Code | Windows Constant | Meaning |
|------|-----------------|---------|
| `0` | `SUCCESS` | Operation completed successfully |
| `1` | `ERROR_INVALID_FUNCTION` | General failure |
| `2` | `ERROR_FILE_NOT_FOUND` | Package or resource not found |
| `5` | `ERROR_ACCESS_DENIED` | Insufficient privileges |
| `1223` | `ERROR_CANCELLED` | Operation cancelled by user |
