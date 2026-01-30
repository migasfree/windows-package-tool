# Tutorial: Getting Started with WPT

Learn how to use **Windows Package Tool** to manage software from the command line.

## Prerequisites

- Windows 10/11 (or Linux for testing)
- Python 3.6 or higher
- Administrative privileges for installation commands

## Step 1: Browse Available Packages

First, see what's available in your configured repositories:

```bash
wpt search
```

If you want to search for a specific tool, use a query:

```bash
wpt search python
```

## Step 2: Install a Package

To install a package, use the `install` command. WPT will automatically handle any dependencies.

```bash
wpt install example-package
```

## Step 3: Check Installation Status

Verify if a package is correctly registered:

```bash
wpt list
```

Or get detailed info:

```bash
wpt status example-package
```

## Step 4: Keep Software Updated

Update your local repository info first:

```bash
wpt update
```

Then upgrade all installed packages:

```bash
wpt upgrade
```

## Step 5: Remove a Package

When you no longer need a tool, remove it cleanly:

```bash
wpt remove example-package
```

## Next Steps

- Learn [How to create your own packages](../how-to/create-package.md)
- Explore the [CLI Reference](../reference/cli.md)
