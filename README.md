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
foodnomsctl log-weight 191.4
foodnomsctl create-food "House Granola" --brand "Homemade" --calories 220 --protein 6
foodnomsctl db-search "skyr"
foodnomsctl ask "how much protein have I had today"
foodnomsctl goal
```

One Shortcut rather than one per intent, because installing a suite of twelve is a chore and
they drift apart. Generated rather than hand-built, because a dispatcher is N branches of
hand-wired parameters — exactly the shape that rots. The branch set is data in `intents.yaml`;
rebuilding re-emits all of it, checks that no two commands collide, and verifies every
conditional block closes.

Dispatch compares the command name for **exact equality**, never "contains". A contains-match
dispatcher is how a branch for `log` also fires for `log-weight`.

### Which intents are wrapped, and why so few

FoodNoms ships 45 App Intents. Nine only open UI and do nothing headless. Most of the rest are
reads that `foodnomsctl` already answers faster and in more detail from the store — wrapping
`GetFoodEntriesIntent` would be strictly worse than `foodnomsctl day`. So the manifest carries
the writes the store must never perform itself, plus the two reads the local store genuinely
cannot answer: `db-search` hits FoodNoms' *online* database rather than your log, and `ask`
reaches FoodNoms AI.

Entity-typed parameters — `mealType`, `foodMeasure`, `favorite` — are not exposed. Shortcuts
resolves an entity through picker UI with no headless equivalent. That is the ceiling of this
approach, and the reason `log` takes a quick entry rather than a library reference.

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

- **Writes need the bridge Shortcut imported once.** Reads work immediately; `doctor` tells you
  whether the write path is installed.
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
