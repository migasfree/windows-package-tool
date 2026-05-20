# Enum & Constants Dictionary

All enumerations, status codes, constants, and named values used across WPT.

---

## Package Status Codes

### Desired Status (`STATUS_DESIRED`)

| Code | Label | When Applied |
|------|-------|-------------|
| `u` | unknown | Initial or cleared state |
| `i` | marked for installation | When `install` begins |
| `r` | marked for removal | When `remove` begins |

### Current Status (`STATUS_CURRENT`)

| Code | Label | When Applied |
|------|-------|-------------|
| `n` | not installed | Before download or after successful removal |
| `i` | successfully installed | After all lifecycle scripts complete successfully |
| `u` | unpacked | After `.tar.gz` extraction, before script execution |
| `h` | partially installed | During script execution (preinst→postinst or prerm→postrm) |

### Status Transition Diagram

```txt
Install:  n → (download) → u → (preinst) → h → (postinst) → i
Remove:   i → (prerm) → h → (postrm) → n
Rollback: h → n  (on script failure during install)
```

---

## GPG Verification Modes

| Value | Effect |
|-------|--------|
| `required` | Repository index download is rejected if signature is missing or invalid |
| `optional` | Signature failure produces a warning but does not block the update |
| `disabled` | No GPG verification is attempted at all |

**Config key:** `[gpg] verify` in `wpt.conf`
**Default:** `optional`

---

## SSL Verification Options

| Value | Effect |
|-------|--------|
| `true` | Verify SSL certificates (recommended) |
| `false` | Disable SSL verification entirely |
| `<path>` | Path to a custom CA certificate bundle (PEM format) |

**Config key:** `[ssl] verify` in `wpt.conf`
**Default:** `true`

---

## Log Levels

| Value | Numeric | Description |
|-------|---------|-------------|
| `DEBUG` | 10 | Verbose diagnostic output |
| `INFO` | 20 | Normal operational messages |
| `WARNING` | 30 | Non-fatal issues |
| `ERROR` | 40 | Failures that affect output |
| `CRITICAL` | 50 | System-level failures |

**Config key:** `[logging] level` in `wpt.conf`
**Default:** `INFO`

---

## Exit Codes

| Code | Windows Constant | POSIX Equivalent | Meaning |
|------|-----------------|------------------|---------|
| `0` | `SUCCESS` | `0` | Successful completion |
| `1` | `ERROR_INVALID_FUNCTION` | `1` | General failure |
| `2` | `ERROR_FILE_NOT_FOUND` | `ENOENT` | Package or resource not found |
| `5` | `ERROR_ACCESS_DENIED` | `EPERM` | Insufficient privileges |
| `1223` | `ERROR_CANCELLED` | `ECANCELED` | Operation cancelled by user |

---

## Package Format Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `PKG_ARCH` | `x64` | Architecture suffix in package filenames |
| `PKG_EXT` | `.tar.gz` | Package archive extension |
| `PKG_METADATA_FILE` | `metadata.json` | Metadata filename inside `pms/` |
| `SOURCES` | `sources.list` | Repository sources filename |
| `REPO_FILE` | `packages.json` | Repository index filename |
| `SCRIPT_MAX_SIZE` | 1 MB | Maximum allowed size for maintainer scripts |

---

## Maintainer Script Execution Order

| Phase | Script | When |
|-------|--------|------|
| Install | `preinst` | Before files are copied |
| Install | `install` | Main copy/installation step |
| Install | `postinst` | After files are copied |
| Remove | `prerm` | Before files are deleted |
| Remove | `remove` | Main deletion step |
| Remove | `postrm` | After files are deleted |

Supported extensions (tried in this order): `.py`, `.cmd`, `.ps1`

---

## Supported Dependency Version Operators

| Operator | Meaning |
|----------|---------|
| `=` | Exactly this version |
| `>` | Strictly greater than |
| `<` | Strictly less than |
| `>=` | Greater than or equal |
| `<=` | Less than or equal |

Dependency format: `<name>` or `<name> (<op> <version>)` (e.g., `mylib (>= 2.0)`)

---

## Windows Registry Paths

| Path | Purpose |
|------|---------|
| `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall` | All installed Windows software (read-only for `wpt list --all`) |
| `HKLM\SOFTWARE\wpt\Packages\<name>` | WPT-managed packages (read/write) |

### WPT Registry Entry Fields

| Value Name | Type | Description |
|------------|------|-------------|
| `Name` | `REG_SZ` | Package name |
| `Version` | `REG_SZ` | Package version |
| `Description` | `REG_SZ` | Package description |
| `Maintainer` | `REG_SZ` | Maintainer name and email |
| `Specification` | `REG_SZ` | Package format version (`1.0.0`) |

---

## Rich CLI Color Theme

| Token | Color | Used For |
|-------|-------|---------|
| `info` | Bold blue | Informational messages |
| `success` | Bold green | Successful operations |
| `warning` | Bold yellow | Non-fatal warnings |
| `error` | Bold red | Error messages |
| `header` | Bold magenta | Table headers |
| `text.inverse` | Reverse | Highlighted text |
| `pkg.name` | Cyan | Package names in tables |
| `pkg.version` | Green | Package versions in tables |
| `url` | Underline cyan | Repository URLs |
