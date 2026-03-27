# Understanding WPT Architecture

Learn about the concepts and design decisions behind Windows Package Tool.

## Design Philosophy

WPT is designed to be **simple**, **transparent**, and **platform-aware**.
While targeted at Windows, its core logic remains compatible with
Unix-like systems for development and testing.

## Key Concepts

### 1. Idempotency

Maintainer scripts must be idempotent. If an installation is interrupted
or run twice, the second run should safely reach the desired state
without causing errors or duplicating files.

### 2. Desired State Tracking

WPT tracks package status in a local `status.json` file. It distinguishes between:

- **Desired state**: What the user wants (`installed`, `removed`).
- **Current state**: The actual state of the system during transitions.

### 3. Dependency Resolution

WPT uses an iterative resolution algorithm with a work queue.
Before installing a package, it builds a dependency tree to ensure
all requirements are met, avoiding "dependency hell."
Circular dependencies are detected and rejected.

## Component Overview

- **`PackageManager`**: The heart of the tool, handling repository updates, downloads, and the installation lifecycle.
- **`logging`**: Centralized logging with rotating file handler for troubleshooting.
- **Maintainer Scripts**: User-provided logic that handles the actual file operations on the host system.
- **Registry Integration**: On Windows, WPT registers packages in the
  system registry for compatibility with other management tools.

## Logging

WPT maintains a persistent log file for troubleshooting:

- **Location**: `%PROGRAMDATA%\wpt\wpt.log`
- **Rotation**: 5MB max size, 3 backup files retained
- **Format**: `[timestamp] [level] message`

The log captures all package operations (install, remove, upgrade), download activity, and errors.

## Limitations

- **Limited Sandbox**: Scripts run with security restrictions (timeout, size limits) but still require administrative privileges.
- **JSON-based**: Relies on JSON for metadata, ensuring readability but requiring valid syntax.
