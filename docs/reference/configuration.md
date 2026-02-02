# Configuration Reference

Windows Package Tool (wpt) uses INI-based configuration files with support for override directories.

## Configuration Files

Configuration is loaded from the following locations in order:

1. **Main configuration file**: `%PROGRAMDATA%\wpt\wpt.conf`
2. **Override directory**: `%PROGRAMDATA%\wpt\conf.d\*.conf` (loaded alphabetically)

Values from later files override earlier ones, allowing customization without modifying the main configuration.

## Configuration Structure

```text
%PROGRAMDATA%\wpt\
├── wpt.conf           # Main configuration file
└── conf.d\            # Override directory
    └── *.conf         # Override files (loaded in alphabetical order)
```

## Auto-deployment

On first run, if the configuration file doesn't exist, wpt automatically:

- Copies the default `wpt.conf` from the package installation
- Creates the `conf.d/` directory

## Configuration Options

### [logging]

| Option  | Type   | Default | Description                                                    |
|---------|--------|---------|----------------------------------------------------------------|
| `level` | string | `INFO`  | Log verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |

**Example:**

```ini
[logging]
level = DEBUG
```

### [ssl]

| Option | Type | Default | Description |
|---|---|---|---|
| `verify` | bool/path | `true` | SSL certificate verification. Set to `false` to disable, or path to CA bundle |

**Example:**

```ini
[ssl]
# Disable verification (not recommended for production)
verify = false

# Or use a custom CA bundle
verify = C:\path\to\ca-bundle.crt
```

> **Note:** Command-line arguments (`--no-check-certificate`, `--ca-cert`) always TAKE PRECEDENCE over these
> configuration settings.

### [scripts]

| Option | Type | Default | Description |
|---|---|---|---|
| `timeout` | integer | `300` | Max execution time in seconds for maintainer scripts |

**Example:**

```ini
[scripts]
timeout = 600
```

## Example Configuration

### Default wpt.conf

```ini
# Windows Package Tool Configuration

[logging]
level = INFO

[ssl]
verify = true

[scripts]
timeout = 300
```

### Override for Development (conf.d/10-development.conf)

```ini
# Development overrides
[logging]
level = DEBUG

[ssl]
verify = false
```

## Log File Location

The log file is stored in the system's temporary directory:

- **Windows**: `%TEMP%\wpt.log`
- **Linux** (for development): `/tmp/wpt.log`

Log rotation is enabled with:

- Maximum size: 5MB per file
- Backup count: 3 files
