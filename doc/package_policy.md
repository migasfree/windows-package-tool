# Package Policy

## Standards Conformance

Source packages should specify the most recent version number of this policy document with which your package complied when it was last updated.

The version is specified in the `specification` metadata field. Actual value must be `1.0.0`. Others values are invalid.

## Package Structure

```
package_directory
  |
  |- pms
  |   |
  |   |- metadata.json
  |   |- [readme.md]
  |   |- [changelog.md]
  |   |- [preinst.{ps1|cmd|py}]
  |   |- [install.{ps1|cmd|py}]
  |   |- [postinst.{ps1|cmd|py}]
  |   |- [prerm.{ps1|cmd|py}]
  |   |- [remove.{ps1|cmd|py}]
  |   |- [postrm.{ps1|cmd|py}]
  |
  |- [data]
```

## Metadata files and their fields

The package management system manipulates data represented in a common format, known as control data, stored in metadata files. The format used for these metadata files is JSON.

The fields in metadata file are:

* `name` (mandatory)
* `version` (mandatory)
* `description` (mandatory)
* `maintainer` (mandatory)
* `specification` (mandatory)
* `dependencies` (optional)
* `homepage` (optional)

### Example of metadata.json file

```json
{
    "name": "example-package",
    "version": "1.0.0",
    "description": "A simple example package",
    "maintainer": "John Doe <jdoe@example.com>",
    "specification": "1.0.0",
    "dependencies": ["other-package (>= 3.6)", "another-package"],
    "homepage": "https://example.com"
}
```

## Package maintainer scripts and installation procedure

It is possible to supply scripts as part of a package which the package management system will run for you when your package is installed, upgraded or removed.

These scripts are the package files `preinst`, `install`, `postinst`, `prerm`, `remove` and `postrm`. The format of these scripts could be `cmd`, `ps1` (powershell) or `py` (python).

* `preinst.{ps1|cmd|py}`: to execute before copy files
* `install.{ps1|cmd|py}`: to copy package files in directories structure
* `postinst.{ps1|cmd|py}`: to execute after copy files
* `prerm.{ps1|cmd|py}`: to execute before remove files
* `remove.{ps1|cmd|py}`: to remove package files from directories structure
* `postrm.{ps1|cmd|py}`: to execute after remove files

### Maintainer scripts idempotency

It is necessary for the error recovery procedures that the scripts be idempotent. This means that if it is run successfully, and then it is called again, it doesn’t bomb out or cause any harm, but just ensures that everything is the way it ought to be. If the first call failed, or aborted half way through for some reason, the second call should merely do the things that were left undone the first time, if any, and exit with a success status if everything is OK.

### Controlling terminal for maintainer scripts

Maintainer scripts are not guaranteed to run with a controlling terminal and may not be able to interact with the user. They must be able to fall back to noninteractive behavior if no controlling terminal is available.

### Exit status

Each script must return a zero exit status for success, or a nonzero one for failure, since the package management system looks for the exit status of these scripts and determines what action to take next based on that datum.

## Repository packages structure

`packages.json`:

```json
{
    "example-package": {
        "1.0.0": {
            "metadata": {
                "description": "blah blah",
                "maintainer": "John Doe <jdoe@example.com>",
                "specification": "1.0.0",
                "dependencies": [],  // optional
                "homepage": "",  // optional
            },
            "filename": "relative_path_to/example-package-1.0.0.tar.gz",
            "hash": "sha256:abc123",
        },
        "2.0.0": {
            "metadata": {
                "description": "blah blah",
                "maintainer": "John Doe <jdoe@example.com>",
                "specification": "1.0.0",
                "dependencies": [],  // optional
                "homepage": "",  // optional
            },
            "filename": "relative_path_to/example-package-2.0.0.tar.gz",
            "hash": "sha256:abc123",
        }
    },
    "another-package": {
        ...
    }
}
```
