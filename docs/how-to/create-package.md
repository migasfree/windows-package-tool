# How to Create a PMS Package

This guide shows you how to bundle software into a WPT package.

## 1. Prepare the Directory Structure

Create a folder for your source files:

```text
my-app-source/
└── pms/
    └── metadata.json
```

## 2. Define Metadata

Create `pms/metadata.json` with your package details:

```json
{
    "name": "my-app",
    "version": "1.0.0",
    "description": "My Awesome Application",
    "maintainer": "Your Name <you@example.com>",
    "specification": "1.0.0"
}
```

## 3. Add Installation Scripts

Create `pms/install.py` to define where files should go. WPT provides several environment variables during execution.

Example `install.py`:

```python
import shutil
import os

# Source data is in the temporary extraction path
# Destination is your target folder
shutil.copytree('data', 'C:/Program Files/MyApp')
```

## 4. Build the Package

Use the `wpt build` command pointing to your source directory:

```bash
wpt build my-app-source/
```

This will generate a `my-app_1.0.0_x86_64.tar.gz` file ready for distribution.

## Best Practices

- **Idempotency**: Ensure your scripts can be run multiple times without failing.
- **Cleanup**: Always provide a `remove.py` script to leave the system clean.
- **Error Handling**: Return non-zero exit codes if something goes wrong.
