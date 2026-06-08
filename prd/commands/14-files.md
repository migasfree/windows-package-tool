# Command: `wpt files`

> **Synopsis:** `wpt files <package>`
> **Module:** Package Discovery
> **Requires Admin:** No
> **Generated:** 2026-06-08

## Overview

Lists all files and directories installed on the system by a specific WPT-managed package. This is the functional equivalent of `dpkg -L <package>` on Debian-based systems.

Each file path is printed on its own line, as an absolute path, in the order stored in the package manifest.

## Parameters

| Argument | Required | Description |
|----------|----------|-------------|
| `package` | Yes | Name of the installed package whose files to list |

## Output

One absolute file path per line. No table, no headers — plain text output suitable for scripting and piping.

**Example:**

```text
C:\ProgramData\wpt\packages\my-tool\bin\my-tool.exe
C:\ProgramData\wpt\packages\my-tool\lib\helper.dll
C:\ProgramData\wpt\packages\my-tool\README.txt
```

If the package is installed but contains no tracked files (e.g. a metapackage that only runs scripts), the command exits successfully with no output.

## Interactions

### Normal file listing

- **Trigger:** `wpt files <package>`
- **Behavior:**
  1. Calls `get_installed_package_status(package)` to verify the package is currently installed.
  2. Resolves the path to the package manifest file at `%PROGRAMDATA%\wpt\info\<package>.list`.
  3. If the `.list` file exists, prints each non-empty line (absolute path) to stdout.
  4. If the `.list` file does not exist (metapackage with no files), exits silently with code `0`.

### Error: package not installed

- **Trigger:** `wpt files <package>` when the package is not installed.
- **Behavior:** Raises `ValueError` → CLI error handler prints `[error]Package <name> is not installed.[/error]` and exits with code `1`.

## Business Rules

- Only packages currently in the **installed** state (`desired=i`, `current=i`) are valid targets. Packages in a removed or partial state are rejected.
- The output is **not sorted** by default — it reflects the order the files were recorded in the manifest at install time (alphabetical, as produced by `create_package_info`).
- The command does **not check whether the listed files still exist** on disk. It reports what was installed, not the current disk state. Use `status` to verify package integrity.
- This command does **not require administrator privileges**.
