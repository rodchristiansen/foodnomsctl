# FoodNomsCTL: The Power-User FoodNoms CLI

FoodNomsCTL is a fast, scriptable [FoodNoms](https://foodnoms.com) CLI for macOS, designed for
power users and AI agents.

FoodNoms is the best nutrition tracker on Apple platforms precisely because it does not want to
be a social network — it wants to log food accurately and get out of the way. What it does not
have is a surface a script can talk to. Your food library, your barcodes, your saved meals and
every macro you have ever logged sit in a local Core Data store that nothing outside the app can
read. FoodNomsCTL reads it.

The insight that makes this useful: **the log is the library.** Every entry FoodNoms writes
carries the food's service identifiers, barcode, unit, serving size and complete nutrition. So
the set of things you have ever logged — with counts, with the units you actually use, with the
brand you are actually buying — is recoverable without any API, any account, and any network.

## Documentation

The full guides live in the **[wiki](https://github.com/rodchristiansen/foodnomsctl/wiki)**. Start here:

| | |
|---|---|
| **[Getting Started](https://github.com/rodchristiansen/foodnomsctl/wiki/Getting-Started)** | Install, run `doctor`, ask your first questions |
| **[What Runs Unattended](https://github.com/rodchristiansen/foodnomsctl/wiki/What-Runs-Unattended)** | Which commands work over SSH, with the screen locked, from a phone — read this before automating anything |
| [Reading Your Library](https://github.com/rodchristiansen/foodnomsctl/wiki/Reading-Your-Library) | `catalog`, `search`, `resolve`, `day`, `meals`, `barcodes` |
| [Writing to FoodNoms](https://github.com/rodchristiansen/foodnomsctl/wiki/Writing-To-FoodNoms) | `log`, `create-food`, the macro rule, what a write costs |
| [The Write Queue](https://github.com/rodchristiansen/foodnomsctl/wiki/The-Write-Queue) | Why writes are queued, the drain agent, the locked-Mac problem |
| [Correcting the Log](https://github.com/rodchristiansen/foodnomsctl/wiki/Correcting-The-Log) | `delete`, `edit`, and when to reach for `relog` |
| [The Bridge Shortcut](https://github.com/rodchristiansen/foodnomsctl/wiki/The-Bridge-Shortcut) | Generating, signing, installing, and naming it |
| [Troubleshooting](https://github.com/rodchristiansen/foodnomsctl/wiki/Troubleshooting) | Every failure seen so far and what it actually meant |
| [How It Works Inside](https://github.com/rodchristiansen/foodnomsctl/wiki/How-It-Works-Inside) | Store discovery, nutrient scaling, the local-day key |
| [Automation Recipes](https://github.com/rodchristiansen/foodnomsctl/wiki/Automation-Recipes) | Worked `--json` pipelines for scripts and agents |
| [Contributing](https://github.com/rodchristiansen/foodnomsctl/wiki/Contributing) | Tests, the fixture, and the house rules |

The wiki is the only copy — edit it there, not in this repository. It is a git repository of its
own (`git clone https://github.com/rodchristiansen/foodnomsctl.wiki.git`) if you would rather
work on the pages locally.

## How It Works

```text
foodnomsctl
  reads:  ~/Library/Containers/<uuid>/Data/Documents/db.db
          (discovered, snapshotted per invocation, opened read-only)
  writes: FoodNomsCTL Bridge.shortcut -> FoodNoms App Intents
  never:  the store itself
```

**The store has to be discovered, never hardcoded.** FoodNoms has moved it twice
and both earlier locations are still on disk, still populated, and both look
plausible: a Core Data store in the app group container that stops in 2022, and a
GRDB copy beside it that stops in 2025. The live one is in the app's sandbox
container, whose directory name is a random UUID that differs per machine, so
`foodnomsctl` matches it by reading each container's identity plist. Point at
either abandoned store and every command answers confidently with data years
stale — `doctor` names the live store and lists the ones it ignored.

Three deliberate constraints:

- **Never writes the store.** Reads go straight to SQLite; every mutation goes through
  FoodNoms' own App Intents. This is not caution for its own sake — the store is
  CloudKit-mirrored (`NSPersistentCloudKitContainer`, and its `ANSCK*` bookkeeping tables are
  right there beside the data). A row inserted behind the app's back gets no CKRecord, so it
  never reaches your phone, and it can leave the export bookkeeping inconsistent with the object
  graph. Same split as [RemCTL](https://github.com/viticci/remctl), which reads the Reminders
  database directly and writes through EventKit.
- **Snapshot before read.** The store is copied — with its `-wal` and `-shm` sidecars — to a
  temporary path before every query, so a running FoodNoms.app never contends on the write-ahead
  log. Reads are consistent and the app never notices.
- **The schema is not a contract.** These are GRDB internals, not a published API, and FoodNoms
  has already migrated once from Core Data. `foodnomsctl doctor` tells you immediately when that
  happens instead of returning quietly wrong answers.

## Quick Start

```bash
git clone https://github.com/rodchristiansen/foodnomsctl.git
cd foodnomsctl
./install.sh
foodnomsctl doctor
foodnomsctl day
```

`doctor` verifies the store is present, readable and shaped as expected, and reports how many
entries, distinct foods and saved meals it can see. Run it first; it is the answer to almost
every "why does this return nothing".

If `doctor` reports that it cannot open the store, the app group container is TCC-protected and
the process running FoodNomsCTL needs Full Disk Access. That is the terminal, or the agent host,
not the CLI itself — macOS attributes the access to the responsible process.

## What works headlessly

Verified against a live 16,495-entry store, not inferred from the metadata.

**Reads need nothing but the file.** They open a snapshot of the store and touch
no other process, so they work over SSH, with FoodNoms closed, and while the
Mac's screen is locked. Every one takes `--json`.

| Command | Typical |
|---|---|
| `doctor` | 0.4s |
| `catalog` | 0.3s |
| `search` · `resolve` | 0.4s |
| `day` · `meals` · `resolve-meal` · `barcodes` | 0.1s |

**Writes need an unlocked GUI session.** They dispatch App Intents through a
Shortcut, and Shortcuts does not run while the screen is locked: `shortcuts run`
hangs until it is killed and an import silently does nothing, neither reporting
an error. That is not a bug this tool can fix — it is what the only supported
write path costs. What it does instead is refuse to lose the write: every one is
queued to a file first, `log` returns in about a tenth of a second with the
request safely on disk, and `flush` — or the launchd agent from
`./install-agent.sh` — drains the queue within a minute of the Mac becoming
usable. With the screen unlocked, `log` completes in about 1.3s and `goal` in
about 3s.

**`log` requires all four core macros.** `requireMacros` is set on
`LogQuickEntryIntent`, and FoodNoms does not fail when one is missing — it puts
up its own prompt ("How much total fat?") and waits, which on a headless run is
a hang, not an error. So `log` refuses up front and names the missing flags.
Fiber, sugars and sodium are genuinely optional. Pass `0` where a macro really
is zero.

```bash
foodnomsctl log "Cold brew" --calories 15 --protein 1 --carbs 0 --fat 0
```

**Nothing else blocks on UI.** The intents that would — the two search intents,
which present the food picker, and `AskFoodnomsAI`, whose `mealType` is
entity-typed — are deliberately not wrapped, for the reasons in
[intents.yaml](intents.yaml) and [docs/app-intents.md](docs/app-intents.md).

## Commands

Every command takes `--json`.

### `day [YYYY-MM-DD]`

The day's log with per-entry macros and totals. Defaults to today.

```bash
foodnomsctl day
foodnomsctl day 2026-08-29
```

### `catalog [--min-count N] [--since YYYY-MM-DD]`

Every distinct food you have ever logged, most-logged first, with the count. The most recent
entry for each food is taken as canonical — units and serving sizes drift as brands change, and
what you logged last is by definition what you are buying now.

```bash
foodnomsctl catalog --min-count 5
foodnomsctl catalog --since 2026-01-01 --json
```

### `search <term>` · `resolve <term>`

`search` finds every matching food and prints its service, identifier and barcode. `resolve`
returns exactly one — the most-logged match — and exits non-zero if there is none, which is what
you want inside a script.

```bash
foodnomsctl search "peanut butter"
foodnomsctl resolve barcode:0068100084245
foodnomsctl resolve "id:12345678"
```

### `meals [name]` · `resolve-meal <name>`

Saved FoodNoms Meals with their items. `resolve-meal` returns the meal's UUID — the same
identifier FoodNoms' `LogMealIntent` takes — so a Shortcut can log a saved meal by name instead
of by a UUID pasted in by hand.

```bash
foodnomsctl meals
foodnomsctl resolve-meal "Morning Smoothie"
```

### `doctor`

Store path, size, entry counts, whether the bridge Shortcut is installed, and a clear failure
when the schema has moved.

The bridge is matched by exact name. Importing a Shortcut never replaces one already in the
library, so a rebuild lands beside the old copy as "FoodNomsCTL Bridge 2" — a substring test
would call the write path healthy while every write fails. `doctor` names the near-miss.

`foodnomsctl --version` prints the version.

## Writing

macOS has no command that invokes another app's App Intent directly, so writes go through one
generated Shortcut. The CLI hands it a JSON request, it dispatches on the `command` key, and
returns the intent's result.

```bash
./foodnomsctl-bridge --publish
```

That generates `FoodNomsCTL Bridge.xml` from [intents.yaml](intents.yaml), signs it, and opens
it for import — importing is a tap you make once in Shortcuts. After that:

```bash
foodnomsctl log "Cold brew" --calories 15 --protein 1
foodnomsctl create-food "House Granola" --brand "Homemade" --calories 220 --protein 6
foodnomsctl goal
```

`delete` and `edit` correct the log rather than only appending to it, and
`log --date` writes to an earlier day. `delete` works by chaining
`GetFoodEntriesIntent` into the delete rather than passing an identifier, which
is what closed [issue 001](docs/issues/001-delete-does-not-bind-a-runtime-entity.md);
it deletes by position in the intent's own list, which is not the store's, so it
resolves against that list rather than inferring an index.

Writes are queued before they are attempted. Shortcuts does not run while the
Mac's screen is locked — `shortcuts run` hangs until it is killed and an import
silently does nothing, and neither reports an error — so a write attempted then
is lost in a way that reports success. `log` detects the lock up front and
returns immediately with the request on disk; `flush` drains the queue, and
`./install-agent.sh` installs a launchd agent that drains it automatically
within a minute of the Mac becoming usable.

```bash
foodnomsctl flush
./install-agent.sh
```

One Shortcut rather than one per intent, because installing a suite of twelve is a chore and
they drift apart. Generated rather than hand-built, because a dispatcher is N branches of
hand-wired parameters — exactly the shape that rots. The branch set is data in `intents.yaml`;
rebuilding re-emits all of it, checks that no two commands collide, and verifies every
conditional block closes.

Dispatch compares the command name for **exact equality**, never "contains" — a contains-match
branch for `log` fires for every future command that starts with it. The same mistake, in the
other direction, is what let `doctor` report a bridge named "FoodNomsCTL Bridge 3" as the
bridge it runs.

### Which intents are wrapped, and why so few

FoodNoms ships 45 App Intents; the manifest wraps five. Nine only open UI and do nothing
headless. Most of the rest are reads that `foodnomsctl` already answers faster and in more
detail from the store — wrapping `GetFoodEntriesIntent` would be strictly worse than
`foodnomsctl day`. So what is left is the writes the store must never perform itself, plus `goal`,
which is state the log does not hold, and `entries`, which is the list `delete`
counts positions in — the intent omits water and drink entries, so its order is
not the store's and has to be observed rather than assumed.

Entity-typed parameters — `mealType`, `foodMeasure`, `favorite` — are not exposed. Shortcuts
resolves an entity through picker UI with no headless equivalent. That is the ceiling of this
approach, and the reason `log` takes a quick entry rather than a library reference.

Two intents that would be genuinely useful are deliberately absent, because the local store
cannot answer what they answer and neither is proven to run headlessly.
`SearchFoodnomsDatabaseIntent` reaches FoodNoms' *online* database and presents the food
picker, so `shortcuts run` never returns — that one is settled, and it cannot be wrapped.
`AskFoodnomsAIIntent` and `LogWeightIntent` are untested here; the first declares a required
entity-typed `mealType` and a `logImmediately` flag, which is the shape that tends not to bind.
Neither ships until it has been run. See [docs/app-intents.md](docs/app-intents.md) for how that
gets established.

## Why This Exists

Nutrition tracking dies at the point of friction. A shortcut that logs a smoothie has to name
each ingredient by identifier, and identifiers change every time a brand changes — so the
automation rots, logging gets skipped, and the data stops being worth having.

With a CLI over the library, that inverts. You scan groceries into FoodNoms once, as you already
do, and everything downstream resolves against what is actually in your log:

```bash
foodnomsctl resolve "oat milk" --json | jq -r '.[0].service_id'
```

Generated automations, agent workflows, weekly reviews and macro reports all become a query
instead of a maintenance chore.

It also matters that this works for **agents**. An AI agent asked "how much protein did I get
yesterday" should answer from the log in milliseconds, not ask you to open an app and read a
number back to it. Structured `--json` on every command is the point, not a convenience.

## Limitations

Stated plainly, because they are structural:

- **Writes need the bridge Shortcut imported once, and an unlocked Mac.** Reads work
  immediately and regardless; `doctor` tells you whether the write path is installed. See
  [what works headlessly](#what-works-headlessly).
- **macOS only.** It reads a local file; there is no iOS equivalent and there cannot be one.
- **Unofficial.** Not affiliated with or endorsed by Algebraic Labs. What would make this
  unnecessary, or merely easier, is collected in
  [docs/feature-requests.md](docs/feature-requests.md). The schema is internal and
  may change without notice — `doctor` is how you find out.
- **Foods you have never logged are invisible.** This reads your library, not FoodNoms' full food
  database. Scan it once and it is queryable forever after.

## Dependencies

`foodnomsctl` is one file and imports only the standard library, so installing
it is a copy and there is nothing to pin. Python 3.10 or newer; CI covers 3.10
and 3.13.

`foodnomsctl-bridge` is the one exception: regenerating the bridge Shortcut
reads `intents.yaml`, so it needs **PyYAML** (`pip3 install pyyaml`). Nothing
else in the tool does.

Beyond Python it needs macOS — it reads a local container path, so there is no
iOS equivalent — the `shortcuts` CLI, FoodNoms installed, and for writes the
bridge Shortcut imported and FoodNoms running (the CLI launches it). The calling
process needs Full Disk Access to read the container; macOS attributes that to
the responsible process, so it is the terminal or the agent host, not the CLI.
A launchd agent does not inherit it, which is why the queue defaults to
`~/.local/state` rather than the iCloud spool.

## Development

One file, no third-party dependencies, stdlib `unittest`. The tests run against a synthetic
store built by `tests/fixture.py`, so they need neither FoodNoms nor your data:

```bash
python3 -m unittest discover -s tests -v
```

What they cover is the arithmetic and the matching — the places where a wrong answer looks like
a right one. Nutrient scaling by the calorie ratio (a tablespoon of a per-100g food is not a
hundred grams), the local-day key against a value read out of a live store, id matching on a
colon boundary, saved-meal components excluded from a day's totals, and the exact-name bridge
check.

## Related

Part of a small suite of `*ctl` tools that give scriptable surfaces to good apps that lack them,
in the spirit of [RemCTL](https://github.com/viticci/remctl) and `notesctl`.

## License

MIT. See [LICENSE](LICENSE).
