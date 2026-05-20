# Configuration Reference

Complete reference for all WPT configuration options.

---

## Configuration File Locations

| File | Purpose |
|------|---------|
| `%PROGRAMDATA%\wpt\wpt.conf` | Main configuration file |
| `%PROGRAMDATA%\wpt\conf.d\*.conf` | Drop-in override files (loaded alphabetically after main file) |

If `wpt.conf` does not exist on first run, WPT automatically copies the bundled template. Drop-in files in `conf.d/` are optional and allow managed deployment of partial config overrides without modifying the main file.

---

## Configuration Sections

### `[logging]`

Controls log verbosity written to `%TEMP%\wpt.log`.

| Key | Type | Default | Valid Values | Description |
|-----|------|---------|--------------|-------------|
| `level` | String | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | Minimum log level |

---

### `[ssl]`

Controls HTTPS certificate verification for all outbound HTTP requests.

| Key | Type | Default | Valid Values | Description |
|-----|------|---------|--------------|-------------|
| `verify` | String/Bool | `true` | `true`, `false`, `<file path>` | SSL verification behavior. A file path must point to a PEM CA bundle. |

> **Note:** The `--no-check-certificate` and `--ca-cert` CLI flags override this setting at runtime.

---

### `[scripts]`

Controls maintainer script execution behavior.

| Key | Type | Default | Valid Values | Description |
|-----|------|---------|--------------|-------------|
| `timeout` | Integer | `300` | Any positive integer | Maximum seconds a maintainer script may run before being killed. |

---

### `[gpg]`

Controls GPG signature verification of repository package indexes.

| Key | Type | Default | Valid Values | Description |
|-----|------|---------|--------------|-------------|
| `verify` | String | `optional` | `required`, `optional`, `disabled` | Signature verification mode. See Enum Dictionary for behavior details. |

---

## Full Example (`wpt.conf`)

```ini
[logging]
level = INFO

[ssl]
verify = true

[scripts]
timeout = 300

[gpg]
verify = optional
```

---

## Drop-in Override Example (`conf.d/10-custom-ca.conf`)

```ini
[ssl]
verify = C:\ProgramData\certs\internal-ca.pem
```

Files in `conf.d/` must have the `.conf` extension to be loaded. They are merged in alphabetical filename order, so naming them with numeric prefixes (`10-`, `20-`) gives predictable merge order.

---

## Runtime Paths

These paths are derived from `PROGRAMDATA` (Windows) or XDG/home directory (fallback). They are not configurable in `wpt.conf`.

| Variable | Default Windows Path |
|----------|---------------------|
| Data directory | `%PROGRAMDATA%\wpt\` |
| Temp directory | `%PROGRAMDATA%\wpt\temp\` |
| Packages directory | `%PROGRAMDATA%\wpt\packages\` |
| Info directory | `%PROGRAMDATA%\wpt\info\` |
| Keys directory | `%PROGRAMDATA%\wpt\keys\` |
| Config file | `%PROGRAMDATA%\wpt\wpt.conf` |
| Config.d directory | `%PROGRAMDATA%\wpt\conf.d\` |
| Sources list | `%PROGRAMDATA%\wpt\sources.list` |
| Repository cache | `%PROGRAMDATA%\wpt\packages.json` |
| Status file | `%PROGRAMDATA%\wpt\status.json` |
| Lock file | `%PROGRAMDATA%\wpt\wpt.lock` |
| Log file | `%TEMP%\wpt.log` |
