# Windows Package Tool (wpt)

A simplified Package Management System for Windows environments, designed for simplicity and reliability.

## 🚀 Quick Start

Get up and running in minutes:

```bash
# Update repository info
wpt update

# Search for a package
wpt search example

# Install
wpt install example-package
```

## 📖 Documentation (Diátaxis)

Our documentation is organized following the [Diátaxis](https://diataxis.fr/) framework:

### 🎓 Tutorials

- [Getting Started](docs/tutorials/getting-started.md): A step-by-step guide for new users.

### 🛠️ How-to Guides

- [Create a Package](docs/how-to/create-package.md)
- [Manage Repositories](docs/how-to/manage-repositories.md)
- [AI Packaging Prompts](docs/how-to/ai-packaging-prompt.md)
- [Package Python Applications](docs/how-to/package-python-app.md)

### 📚 Reference

- [CLI Reference](docs/reference/cli.md): Commands, arguments, and options.
- [Configuration](docs/reference/configuration.md): Configuration files and options.
- [Package Format](docs/reference/package-format.md): Technical specification of WPT packages.

### 🧠 Explanation

- [Architecture](docs/explanation/architecture.md): Conceptual overview and design goals.
- [Value Proposition](docs/explanation/value-proposition.md): The gap WPT fills in the Windows ecosystem.

## 🛠️ Installation (Development)

```bash
git clone https://github.com/migasfree/windows-package-tool
cd windows-package-tool
pip install -e .
```

## 📋 System Requirements

WPT requires the following system components:

- **Python >= 3.6**
- **GnuPG (gpg)**: Specifically required for repository signature verification (`wpt update`, `wpt import-key`).

## ⚖️ License

This project is licensed under the GPL-3.0-or-later License.
