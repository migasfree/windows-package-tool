# CLI Reference

Technical reference for the `wpt` command-line interface.

## Global Options

| Option | Description |
| :--- | :--- |
| `-h, --help` | Show help message and exit |
| `-q, --quiet` | Perform operations with minimal (or null) output |
| `-y, --assume-yes` | Automatic yes to prompts |

## Commands

### `install`

Installs packages to the system.

**Arguments**:

- `package`: Name of the package to install. Supports `name=version` format.

---

### `remove`

Removes packages from the system.

**Usage**: `wpt remove [-h] [-f] package [package ...]`

**Arguments**:

- `package`: Name of the package to remove.

**Options**:

- `-f, --force`: Forces removal without checking dependencies.

---

### `list`

Lists installed packages.

**Usage**: `wpt list [-h] [-a] [-s]`

**Options**:

- `-a, --all`: List all installed software (including system software).
- `-s, --summary`: Display a summary (name_version_arch).

---

### `search`

Searches for available packages in repositories.

**Usage**: `wpt search [-h] [-s] [query]`

**Arguments**:

- `query`: The search pattern (defaults to `*`).

---

### `upgrade`

Upgrades all installed packages to their latest versions.

**Usage**: `wpt upgrade`

---

### `update`

Reads online repositories and updates local cache.

**Usage**: `wpt update`

---

### `build`

Creates a PMS package from a directory.

**Usage**: `wpt build [-h] directory`

---

### `clean`

Cleans the PMS temporary cache.

**Usage**: `wpt clean`

---

### `status`

Returns the status of a specific package.

**Usage**: `wpt status [-h] [-i] package`

**Options**:

- `-i, --is-installed`: Returns exit code indicating if the package is installed.
