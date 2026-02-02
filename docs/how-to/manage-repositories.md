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

## Signed Repositories (Security)

WPT supports repository signature verification to ensure the integrity of the downloaded packages.

### Requirements

- **GnuPG (gpg)** must be installed on the system.
- The repository must provide a `packages.json.sig` file.

### Trusting a Repository

To verify signatures, you must first trust the repository's public key:

1. Download the repository's public key (e.g., `repo.pub`).
2. Import the key into WPT:

    ```bash
    wpt import-key repo.pub
    ```

3. Configure WPT to require signatures in `wpt.conf`:

    ```ini
    [gpg]
    verify = required
    ```

## Refreshing Local Cache

After changing repositories or adding keys, always run:

```bash
wpt update
```
