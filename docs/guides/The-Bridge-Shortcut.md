# The Bridge Shortcut

macOS has no command that invokes another app's App Intent directly. The only supported path is
a Shortcut, so every write goes through exactly one: the CLI hands it a JSON request, it
dispatches on a `command` key to the matching FoodNoms intent, and returns the result.

One Shortcut rather than one per intent, because installing a suite of twelve is a chore and
they drift apart. Generated rather than hand-built, because a dispatcher is N branches of
hand-wired parameters — exactly the shape that rots. The branch set is data in `intents.yaml`.

## Building and installing

```bash
./foodnomsctl-bridge --publish
```

Regenerates the Shortcut from the manifest, checks that no two commands collide and that every
conditional block closes, signs it `--mode anyone`, imports it, and confirms it landed.

Needs **PyYAML** (`pip3 install pyyaml`). This is the only third-party dependency in the project.

## Naming, and why it matters more than it should

**Importing never replaces.** A Shortcut already in the library under that name stays, and the
import either is refused or arrives as `FoodNomsCTL Bridge 2`. The `shortcuts` CLI is
`run`/`list`/`view`/`sign` — it cannot delete — so a rebuild under the canonical name can
install nothing while the old build keeps answering.

Set which Shortcut the CLI dispatches to:

```bash
export FOODNOMSCTL_BRIDGE="FoodNomsCTL Bridge 3"
```

That lets a new build be tested before it takes over.

`doctor` matches the bridge by **exact name** and names any near-miss:

```
  [WARN] write path: "FoodNomsCTL Bridge" not installed — reads work, writes will fail.
  [note] "FoodNomsCTL Bridge 3" is in the library but is not the name the CLI runs.
```

A substring test here once reported the write path healthy while every write failed with
"Couldn't find shortcut".

## What silently swallows an import

Three things, none of which report an error:

- **A locked screen.** Shortcuts will not import or run.
- **An open Shortcuts editor window.** Close it and retry.
- **A bare `open`.** `open file.shortcut` hands the file to LaunchServices, which returns 0
  having installed nothing, and `-600` when Shortcuts is not running. Always `open -a Shortcuts`.

Because of all this, never assume an import worked — read the library back.

## Reading the library needs its WAL

`shortcuts list` and a plain copy of `~/Library/Shortcuts/Shortcuts.sqlite` both read a snapshot
from the last checkpoint and can be a day stale. Copy the `-wal` and `-shm` alongside it. This
has produced two confident wrong conclusions: that imports were failing when they had succeeded,
and that deletions had not landed when they had.

**Never write to `Shortcuts.sqlite`.** It is CloudKit-mirrored and editing it desyncs every
device.

## Which intents are wrapped

Five: `log`, `create-food`, `delete`, `entries`, `goal`. FoodNoms ships 45.

Nine only open UI. Most of the rest are reads the store answers faster and in more detail —
wrapping `GetFoodEntriesIntent` would be strictly worse than `foodnomsctl day` — so what is left
is the writes the store must never perform itself, plus `goal`, which the log does not hold, and
`entries`, which is the list `delete` counts positions in.

Three that would be useful cannot be wrapped at all; see
[What Runs Unattended](What-Runs-Unattended.md).

One trap worth knowing: **Shortcuts validates every action before running any of them.** A
single unbindable parameter anywhere makes the whole bridge return "Please choose a value for
each parameter in this action" — including for commands that are themselves fine. Speculative
intents cannot simply be added and left unused.
