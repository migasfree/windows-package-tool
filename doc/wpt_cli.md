# Command-Line Interface

```cmd
wpt
usage: wpt [-h] [-q] [-y] {install,remove,list,search,upgrade,update,build,clean,status} ...

Windows Package Tool: A simple package management system

positional arguments:
  {install,remove,list,search,upgrade,update,build,clean,status}
    install             install packages to system
    remove              remove packages from system
    list                list installed packages
    search              searchs in available packages
    upgrade             upgrades installed packages in system
    update              reads online repositories and updates local one
    build               creates a PMS package
    clean               cleans PMS cache
    status              returns package status

options:
  -h, --help            show this help message and exit
  -q, --quiet           perform operations with minimal (or null) output
  -y, --assume-yes      automatic yes to prompts
```

## Install command

```cmd
wpt install --help
usage: wpt install [-h] package [package ...]

positional arguments:
  package     the name of the package to install

options:
  -h, --help  show this help message and exit
```

## Remove command

```cmd
wpt remove --help
usage: wpt remove [-h] [-f] package [package ...]

positional arguments:
  package      the name of the package to remove

options:
  -h, --help   show this help message and exit
  -f, --force  forces remove package without check dependencies
```

## List command

```cmd
wpt list --help
usage: wpt list [-h] [-a] [-s]

options:
  -h, --help     show this help message and exit
  -a, --all      list all packages
  -s, --summary  display a summary of the packages
```

## Search command

```cmd
wpt search --help
usage: wpt search [-h] [-s] [query]

positional arguments:
  query          the search query

options:
  -h, --help     show this help message and exit
  -s, --summary  display a summary of the packages
```

## Status command

```cmd
wpt status --help
usage: wpt status [-h] [-i] package

positional arguments:
  package             the name of the package to check the status of

options:
  -h, --help          show this help message and exit
  -i, --is-installed  return exit code indicating if the package is installed or not
```

## Build command

```cmd
wpt build --help
usage: wpt build [-h] directory

positional arguments:
  directory   the directory containing package files

options:
  -h, --help  show this help message and exit
```