# Command: `wpt config`

> **Synopsis:** `wpt config`
> **Module:** Configuration
> **Requires Admin:** No
> **Generated:** 2026-06-07

## Overview

Shows configuration information, including all loaded configuration files and a formatted table of effective configuration values with their origins (default values or specific configuration files).

## Layout

Terminal output formatted with Rich. Prints a list of loaded files, followed by an "Effective Configuration" table containing:

- **Key**: Config property represented as `<section>.<option>`
- **Value**: The current active value of the option
- **Origin**: Where the value came from (`default`, the main `wpt.conf` file, or a drop-in override under `conf.d/`)

## Parameters

None.

## Interactions

### Configuration Inspection Flow

- **Trigger:** `wpt config`
- **Behavior:**
  1. Gathers all loaded configuration files from the config manager (`_loaded_files`).
  2. Prints the list of loaded configuration files in order of precedence (starting with `[default]`).
  3. Iterates over all options in the active config parser.
  4. Resolves the origin of each option by checking `origins`.
  5. Renders a formatted Rich table containing the sorted options, their resolved values, and their respective origins.

## Business Rules

- **Access Level**: Does not require Administrator elevation.
- **Precedence Order**: Defaults are loaded first, followed by `%PROGRAMDATA%\wpt\wpt.conf` (main configuration file), and then files under `%PROGRAMDATA%\wpt\conf.d\` loaded alphabetically. Later configurations overwrite previous ones, and the origin tracking points to the last file that successfully modified the option.
- **Rich formatting**: Respects `--quiet` global CLI option by suppressing console tables if set.
