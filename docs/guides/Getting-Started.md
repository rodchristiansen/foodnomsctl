# Getting Started

## Install

```bash
git clone https://github.com/rodchristiansen/foodnomsctl.git
cd foodnomsctl
./install.sh
```

`install.sh` copies one file to `~/.local/bin`. There is nothing to build and nothing to pin —
`foodnomsctl` imports only the Python standard library and needs 3.10 or newer.

If `~/.local/bin` is not on your `PATH`, the installer says so and prints the line to add.

## Check it can see your data

```bash
foodnomsctl doctor
```

This is the answer to almost every "why does this return nothing", so run it first. A healthy
report names the live store, the size and modification time, how many entries and distinct foods
it can see, and whether the write path is installed:

```
foodnomsctl doctor

  [OK]   store /Users/you/Library/Containers/<uuid>/Data/Documents/db.db
         90.3 MB, modified 2026-09-05 19:32
  [note] ignoring abandoned store ~/Library/Group Containers/group.com.algebraiclabs.foodnoms/FoodNoms.sqlite
  [OK]   16495 logged entries, newest 2026-09-05 20:21:44
  [OK]   6340 distinct foods
  [OK]   55 saved meals
  [OK]   write path: "FoodNomsCTL Bridge" installed
```

The `[note]` lines are not warnings. FoodNoms has moved its database twice and both earlier
copies are still on disk and still populated — one stops in 2022, the other in 2025. `doctor`
names them so you can see they were considered and skipped.

**If it cannot open the store**, the container is TCC-protected and the process running
`foodnomsctl` needs Full Disk Access. That is your terminal, or whatever host runs your agent,
not the CLI itself — macOS attributes the access to the responsible process.

## Ask it something

```bash
foodnomsctl day
foodnomsctl search "peanut butter"
foodnomsctl catalog --min-count 10
```

`day` with no argument is today. `catalog` is every distinct food you have ever logged, most
logged first. `search` matches on name, or on `barcode:` and `id:` prefixes.

Every command takes `--json`, before or after the subcommand.

## Set up writing, if you want it

Reads work immediately. Writing needs a Shortcut installed once:

```bash
./foodnomsctl-bridge --publish
```

That regenerates the bridge from `intents.yaml`, signs it, imports it and confirms it landed.
It needs **PyYAML** (`pip3 install pyyaml`) — the only third-party dependency anywhere in the
project, and only for this step.

Then read [Writing to FoodNoms](Writing-To-FoodNoms.md), which has one rule you must know before
your first `log`.
