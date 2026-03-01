# AGENTS.md

> **Context for AI Agents working on `windows-package-tool` (wpt)**
> This file provides the essential context, commands, and conventions for AI agents to work effectively on this project.

## 1. Project Overview

**Windows Package Tool (wpt)** is a simplified Package Management System (PMS) for Windows environments, designed to integrate with the Migasfree Systems Management ecosystem. It replicates, on Windows, a package management experience similar to APT/DNF on Linux.

- **Language**: Python 3.6+
- **Platform**: Windows 10 / 11 (with optional Windows-only deps: `pywin32`, `wmi`).
- **Security**: GPG signature verification for repository integrity.
- **Integration**: Acts as a `PMS` backend for `migasfree-client` on Windows machines.

## 2. Setup & Commands

Always use a virtual environment (e.g., `.venv`).

- **Install Dependencies**: `pip install -e .[dev]`
- **Run WPT (CLI)**: `wpt update`, `wpt install <pkg>`, `wpt search <term>`
- **Run Tests**: `pytest`
- **Lint Code**: `ruff check .`
- **Format Code**: `ruff format .`

## 3. Code Style & Conventions

- **Compatibility**: Code MUST be compatible with **Python 3.6+**.
- **Linter/Formatter**: Ruff is authoritative for both linting and formatting.
- **Quote Style**: Single quotes (`'`) are preferred.
- **GPG**: Package signature verification relies on an external `gpg` binary. Ensure it is present in the system `PATH`.
- **Config**: Configuration files are located in `conf/wpt.conf` and installed to `%PROGRAMDATA%\wpt\`.

## 4. Architecture Standards

- **`wpt/`**: Main package module.
  - `wpt/__main__.py`: CLI entry point defining all subcommands.
  - `wpt/repository.py`: Logic for `wpt update` and repository management.
  - `wpt/package.py`: Install, remove, and search logic.
  - `wpt/gpg.py`: Wrapper for GPG signature verification.
- **`conf/`**: Default configuration templates.
- **`docs/`**: Full Diátaxis-structured documentation.
- **`tests/`**: Unit tests using `pytest` and `pytest-mock`.

## 5. Available Skills & Specialized Constraints

This project has no `.agent/skills` directory. Apply the following generalist skills when needed:

- **Python Language**: Pythonic patterns, quality, and Python 3.6+ compatibility.
- **QA & Testing**: Testing patterns with `pytest` and mock strategies.
- **Security**: GPG key management and Windows integrity flows.
- **Documentation**: Diátaxis-structured docs as per `docs/` directory.

## 6. Critical Rules

1. **Python 3.6 Support**: DO NOT use Python features that break compatibility with version 3.6 (e.g., f-strings with `=` specifiers, `walrus :=` operator, `match` statement).
2. **Package Format Integrity**: The WPT package format specification (`docs/reference/package-format.md`) MUST be kept in sync if the binary format is changed.
3. **GPG Dependency**: `wpt update` and signature verification require `gpg` to be installed. Any changes must handle the case where `gpg` is not found gracefully.
4. **Windows-only Code**: Wrap Windows-specific imports (`pywin32`, `wmi`) with `sys_platform == 'win32'` guards to avoid crashes on Linux dev environments.
