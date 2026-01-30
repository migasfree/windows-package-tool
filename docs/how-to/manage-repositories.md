# How to Manage Repositories

Configure where WPT looks for software packages.

## Adding a Repository

WPT looks for repository URLs in the `sources.json` file.

1. Locate your `sources.json` (usually in the application directory).
2. Add the base URL of your repository:

```json
[
    "https://packages.example.com/repo",
    "https://another-repo.org/stable"
]
```

## Repository Structure

An HTTP/S repository must host:
1. A `packages.json` file describing all available versions.
2. The `.tar.gz` package files.

Example `packages.json`:
```json
{
    "my-app": {
        "1.0.0": {
            "metadata": { ... },
            "filename": "my-app_1.0.0_x86_64.tar.gz",
            "hash": "sha256:..."
        }
    }
}
```

## Refreshing Local Cache

After changing repositories, always run:

```bash
wpt update
```
