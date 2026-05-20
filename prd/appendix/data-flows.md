# Data Flow & Component Relationships

How WPT components interact and what data flows between them.

---

## Component Architecture

```txt
CLI (wpt/__main__.py)
    │
    ├─ parse_args()          ← argparse: subcommands + global flags
    ├─ is_admin()            ← Windows API check
    ├─ ensure_single_instance() ← File lock on wpt.lock
    │
    └─ PackageManager
           │
           ├─ PackageManagerBase    (shared state: config, console, verify, quiet, assume_yes)
           ├─ RepositoryMixin       (update, download_package, _get_package_metadata)
           ├─ InstallMixin          (install_package, configure_package, resolve_dependencies, upgrade)
           ├─ RemoveMixin           (remove_package, deconfigure_package, clean)
           ├─ QueryMixin            (list, search, status, info, get_installed_packages)
           ├─ BuildMixin            (build)
           └─ RegistryMixin         (Windows Registry read/write)
```

---

## Data Files & Their Roles

| File | Location | Format | Owner | Description |
|------|----------|--------|-------|-------------|
| `wpt.conf` | `%PROGRAMDATA%\wpt\` | INI | Admin | Main configuration |
| `conf.d/*.conf` | `%PROGRAMDATA%\wpt\conf.d\` | INI | Admin | Layered config overrides |
| `sources.list` | `%PROGRAMDATA%\wpt\` | Text (one URL per line) | Admin | Repository source URLs |
| `packages.json` | `%PROGRAMDATA%\wpt\` | JSON | WPT (generated) | Local repository cache |
| `status.json` | `%PROGRAMDATA%\wpt\` | JSON | WPT (generated) | Install/remove state for all packages |
| `info/<name>.metadata.json` | `%PROGRAMDATA%\wpt\info\` | JSON | WPT (generated) | Per-package metadata copy |
| `info/<name>.list` | `%PROGRAMDATA%\wpt\info\` | Text | WPT (generated) | Manifest of installed data files |
| `info/<name>.<script>.<ext>` | `%PROGRAMDATA%\wpt\info\` | Script | WPT (generated) | Lifecycle script copies |
| `packages/<name>/` | `%PROGRAMDATA%\wpt\packages\` | Directory | WPT (generated) | Managed payload files |
| `temp/` | `%PROGRAMDATA%\wpt\temp\` | Directory | WPT (working) | Download and extraction workspace |
| `wpt.lock` | `%PROGRAMDATA%\wpt\` | Binary lock | WPT (generated) | Single-instance enforcement |
| `wpt.log` | `%TEMP%\` | Text | WPT (generated) | Rotating log file (max 5 MB, 3 backups) |

---

## `status.json` Schema

```json
{
  "<package_name>": {
    "<version>": {
      "status": {
        "desired": "i|r|u",
        "current": "i|n|u|h"
      },
      "install_date": "<ISO8601 timestamp>",  // optional
      "remove_date": "<ISO8601 timestamp>"    // optional
    }
  }
}
```

---

## `packages.json` Schema (Repository Cache)

```json
{
  "<package_name>": {
    "<version>": {
      "filename": "<name>_<version>_x64.tar.gz",
      "hash": "<sha256hex>",
      "metadata": {
        "name": "<name>",
        "version": "<version>",
        "description": "<text>",
        "maintainer": "<name> <email>",
        "specification": "1.0.0",
        "dependencies": ["<dep> (<op> <ver>)"],
        "homepage": "<url>",
        "url": "<repo_base_url>"   // injected by wpt update
      }
    }
  }
}
```

---

## Command Dependency Map

| Command | Reads | Writes | Calls |
|---------|-------|--------|-------|
| `update` | `sources.list` | `packages.json` | GPG binary |
| `install` | `packages.json`, `status.json` | `status.json`, `info/`, `packages/`, Registry | `update` (if cache empty), `remove` (for upgrade) |
| `remove` | `status.json`, `info/`, `packages.json` | `status.json`, Registry | — |
| `upgrade` | `status.json`, `packages.json` | (via install + remove) | `update`, `remove`, `install` |
| `clean` | — | `temp/`, `packages.json` | — |
| `list` | Registry | — | — |
| `search` | `packages.json` | — | `update` (if cache empty) |
| `status` | `status.json`, `packages.json`, `info/` | — | — |
| `info` | `packages.json`, `status.json`, `info/` | — | — |
| `build` | Source directory | `.tar.gz` output | — |
| `download` | `packages.json` | `<output_dir>/<pkg>.tar.gz` | — |
| `import-key` | Key file | GPG keyring | GPG binary |

---

## Integration with migasfree-client

WPT is called as a subprocess by `migasfree-client` on Windows systems, acting as the PMS (Package Management System) backend. Key integration points:

- `migasfree-client` calls `wpt install <package>` and `wpt remove <package>` to manage software deployment.
- `wpt status --is-installed <package>` is used for idempotency checks (exit code only, no text parsing).
- `wpt list --summary` provides a compact package inventory for reporting.
- `wpt update` is called before bulk deployments to ensure the catalog is fresh.
- All calls use `--quiet` to suppress interactive output.
- All calls use `--assume-yes` to prevent interactive prompts from blocking the pipeline.
