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

## How It Works

```text
foodnomsctl
  reads: ~/Library/Group Containers/group.com.algebraiclabs.foodnoms/FoodNoms.sqlite
         (snapshotted per invocation, opened read-only)
  writes: nothing
```

Three deliberate constraints:

- **Read-only, always.** FoodNomsCTL never writes to the store, and has no `--force` that
  changes this. FoodNoms owns its data and its CloudKit sync; a CLI mutating Core Data behind a
  running app is how you corrupt a database and lose a year of logging. Writing is what
  FoodNoms' own App Intents are for.
- **Snapshot before read.** The store is copied — with its `-wal` and `-shm` sidecars — to a
  temporary path before every query, so a running FoodNoms.app never contends on the write-ahead
  log. Reads are consistent and the app never notices.
- **The schema is not a contract.** These are Core Data internals, not a published API. A
  FoodNoms model migration can move them. `foodnomsctl doctor` tells you immediately when that
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

Store path, size, entry counts, and a clear failure when the schema has moved.

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

- **Read-only.** Logging food is FoodNoms' job. Use its App Intents from Shortcuts.
- **macOS only.** It reads a local file; there is no iOS equivalent and there cannot be one.
- **Unofficial.** Not affiliated with or endorsed by Algebraic Labs. The schema is internal and
  may change without notice — `doctor` is how you find out.
- **Foods you have never logged are invisible.** This reads your library, not FoodNoms' full food
  database. Scan it once and it is queryable forever after.

## Related

Part of a small suite of `*ctl` tools that give scriptable surfaces to good apps that lack them,
in the spirit of [RemCTL](https://github.com/viticci/remctl) and `notesctl`.

## License

MIT. See [LICENSE](LICENSE).
