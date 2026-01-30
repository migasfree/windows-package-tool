# Package Format Reference

Technical specification for `wpt` packages and metadata.

## Package Structure

A `.tar.gz` package must follow this internal structure:

```text
package_directory/
├── pms/
│   ├── metadata.json       # Mandatory metadata
│   ├── [readme.md]         # Optional documentation
│   ├── [changelog.md]      # Optional history
│   ├── [preinst.py|ps1]    # Maintainer scripts
│   ├── [install.py|ps1]
│   ├── [postinst.py|ps1]
│   ├── [prerm.py|ps1]
│   ├── [remove.py|ps1]
│   └── [postrm.py|ps1]
└── [data]/                 # Optional payload files
```

## Metadata Fields (`metadata.json`)

| Field | Required | Description |
| :--- | :--- | :--- |
| `name` | Yes | Unique package identifier |
| `version` | Yes | Semantic versioning string |
| `description` | Yes | Brief description of the package |
| `maintainer` | Yes | Name and email (e.g., `User <user@example.com>`) |
| `specification` | Yes | Policy version (must be `1.0.0`) |
| `dependencies` | No | List of required packages (e.g., `["pkg (>= 1.2)"]`) |
| `homepage` | No | URL to project home |

## Maintainer Scripts

Scripts can be written in Python (`.py`), PowerShell (`.ps1`), or Batch (`.cmd`).

| Script | Phase |
| :--- | :--- |
| `preinst` | Executes before files are copied |
| `install` | Responsible for copying data files |
| `postinst` | Executes after files are copied |
| `prerm` | Executes before removal starts |
| `remove` | Responsible for deleting files |
| `postrm` | Executes after removal is finished |

> [!IMPORTANT]
> All scripts must be **idempotent** and return a zero exit status for success.
