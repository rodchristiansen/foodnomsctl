# Changelog

## 0.1.0 — 2026-08-30

First cut, extracted from a personal automation engine where it had been running against a live
FoodNoms library since 2026-08-30.

- `catalog` — every distinct food ever logged, most-logged first, deduplicated by service id
- `search` / `resolve` — find a food by name, `barcode:` or `id:`; `resolve` returns exactly one
- `day` — a day's entries with totals, excluding saved-meal and recipe components
- `meals` / `resolve-meal` — saved Meals and their `LogMealIntent` UUIDs
- `doctor` — store presence, readability, counts, and a clear failure on schema drift
- `--json` on every subcommand

## 0.2.0 — 2026-08-30

Adds the write path. Reads still go straight to SQLite; nothing ever writes the store.

- `foodnomsctl-bridge` — generates the dispatcher Shortcut from `intents.yaml`, verifies every
  conditional block closes and that no two commands collide, and signs it
- `log`, `log-weight`, `create-food`, `db-search`, `ask`, `goal` — App Intent calls dispatched
  through the bridge with `shortcuts run`
- `doctor` now reports whether the bridge is installed
- `--json` works after the subcommand as well as before

## 0.3.0 — 2026-08-30

- Reads the **live** store. FoodNoms migrated from Core Data to GRDB and moved into the app's
  sandbox container; the two earlier stores are still on disk, still answer queries, and stop in
  2022 and 2025 respectively. The store is now discovered by matching each container's identity
  plist, and `doctor` names the one it chose plus the ones it skipped.
- Correct macros. `nutrients` is per base amount, and scaling by quantity × measure only holds
  when the logged unit is the base unit — a tablespoon of a per-100 g food came out ten times
  too large. The factor now comes from the already-scaled `calories` column.
- Correct days. Filtering moved from the UTC `date` to the local-day `day` column; a date window
  took yesterday evening and dropped this evening.
- `delete` — present but **not working**. An entity parameter binds from a literal known at
  build time, not from a value arriving at run time; the intent accepts the request and does
  nothing. The command verifies against the store and fails loudly rather than reporting a
  success that did not happen. The fix is to have the shortcut find the entity itself rather
  than be handed an identifier.
- `--json` before the subcommand is no longer silently un-set by the subparser's own default.

## 0.4.0 — 2026-08-31

- `docs/app-intents.md` — what FoodNoms' App Intents accept, as opposed to what their metadata
  declares. FoodNoms replaced `LogFoodIntent` and `LogDrinkIntent` with a single `LogIntent`,
  silently breaking every Shortcut written against the old identifiers; the new one takes a
  JSON-document entity identifier, requires an `AppIntentDescriptor`, and fails when you supply
  the parameters it declares as required. Also records that `SearchFoodLibraryIntent` opens a
  picker despite claiming not to, that `quantity` does nothing without a `foodMeasure`, and how
  to read an entity shape back out of `Shortcuts.sqlite` instead of guessing it.
- `type: drink` is accepted only for FoodNoms' own drink entries — water logs, a milk sent that
  way fails with "An unknown error occurred" and logs fine as `type: food`.
- Test one food per throwaway Shortcut. A Shortcut stops at its first failing action, so running
  a menu-driven one finds only the first bad food, behind prompts `shortcuts run` cannot answer.
- `search` and `resolve` report each food's `measure` and full `measures` list, which is what a
  generator needs to write a `foodMeasure` — the intent's measure identifier is that dictionary
  wrapped in a `value` key.

## 0.5.0 — 2026-09-05

The first release meant to be handed to someone else, and the one that makes the write
path survive a locked Mac.

The CLI can now correct the log, not only append to it.

- `log --date` — log to an earlier day. `LogQuickEntryIntent` has always declared an optional
  `date`; the bridge never bound it, so every entry landed at "now" and the limitation looked
  like FoodNoms'. A bare `YYYY-MM-DD` logs at noon, because FoodNoms buckets by local day and
  midnight is the boundary a timezone offset pushes across.
- `delete` — works, closing issue 001. `DeleteLoggedFoodIntent` takes an entity array, which
  binds from another action's output but never from an identifier passed at run time, so the
  branch chains `GetFoodEntriesIntent` → `Get Item from List` → delete.
- `entries` — one day's entries as the intent returns them. A read the store answers faster,
  wrapped because it is the list `delete` counts positions in: the intent omits water and
  drink entries, so its order is not the store's and has to be observed rather than assumed.
- `edit` — correct an entry's macros, or move it to another day. `--scale 0.5` for half of
  what was logged. There is no edit-a-logged-entry intent in FoodNoms' 45, so this is delete
  plus re-log, and the re-log is a quick entry: the barcode and serving measure do not
  survive. It says so before doing it. Use `foodnomsctl-relog` when they must.
- `foodnomsctl-relog` — the same correction, keeping the food. LogIntent selects its food and
  portion through entity-typed parameters, and Shortcuts resolves an entity when the action is
  written rather than when it runs, so an entity binds from a literal baked in at build time
  or from another action's output, never from a value in a request. Both shapes were tried
  against the dispatcher: the one an editor saves makes a plist Shortcuts refuses to import,
  and the one that imports asks the user to pick a food instead of logging one. So `relog`
  generates a one-shot Shortcut per batch with the foods written in as literals, installs it,
  deletes the originals and runs it. Deletion happens only after the Shortcut is installed,
  because an entry deleted with no replacement waiting is the one unrecoverable state here.
- Timeout 25s → 90s. The timeout pkills `shortcuts run`, so a write still in flight died with
  it and was reported as "the intent did not return" — which reads like the known
  does-not-return case and was this tool killing its own write. A cold FoodNoms needs over 30s.
- `--publish` uses `open -a Shortcuts` and checks the library afterwards. A bare `open` hands
  the file to LaunchServices, which returns 0 having installed nothing.
- `FOODNOMSCTL_BRIDGE` overrides which Shortcut the CLI dispatches to, so a new build can be
  tested before it takes over. Importing does not replace a same-named Shortcut and the
  `shortcuts` CLI cannot delete, so a rebuild under the canonical name installs nothing.

Timestamps are stored in UTC and every intent reads what it is handed as local time, so `edit`
converts before writing back. Without it an entry moved by the UTC offset — seven hours in
Vancouver, enough to slide a late entry onto the next day and change two days' totals.

Writes are queued, and a locked screen no longer loses them.

- Every write is queued to a file before it is attempted and removed only once the store
  confirms it. Shortcuts does not run while the Mac's screen is locked — `shortcuts run` hangs
  until it is killed and an import silently does nothing — and neither reports an error, so the
  CLI read it as the known does-not-return case and nine backdated entries reported "submitted"
  and wrote nothing. A locked screen is now detected up front, so `log` returns in a tenth of a
  second with the request safe on disk.
- `flush`, and a launchd agent (`install-agent.sh`) that runs it on an interval and on any
  change to the queue directory, so everything queued lands within a minute of the Mac becoming
  usable. No GUI step and nothing to re-enter.
- The 90s wait is gone. The log intent completes the write and never hands control back, so
  waiting for a return value was waiting for something that does not exist; nine items cost
  thirteen minutes. Polling the store for the entry costs a couple of seconds, and the flat wait
  survives only as the cap for a write that never appears at all.
- Draining takes an exclusive lock and a second drainer leaves rather than waits. The agent
  drains on an interval *and* on directory change, so a hand-started drain ran beside an
  agent-started one, both dispatched the same request before either had landed, and nine queued
  items became ninety entries in the log. Each request is also claimed by renaming it out of
  `pending` before it is read: a crash leaves it claimed rather than pending, because
  re-entering a missing meal beats unpicking a duplicated one.
- The queue defaults to `~/.local/state/foodnomsctl/queue`, not the iCloud spool — a launchd
  agent does not inherit the terminal's Full Disk Access and dies on `PermissionError` reading
  anything under `~/Library/Mobile Documents`. `FOODNOMSCTL_SPOOL` points it elsewhere.

It is also the first release with tests.

- `doctor` matches the bridge by **exact name**. Importing never replaces one already in the
  library, so a rebuild lands beside the old copy as "FoodNomsCTL Bridge 2" and a substring test
  reported the write path healthy while every write failed with "Couldn't find shortcut".
- `--version`.
- Tests — stdlib `unittest` over a synthetic store, so they need neither FoodNoms nor your data:
  `python3 -m unittest discover -s tests`. They cover nutrient scaling, the local-day key, id
  matching, saved-meal exclusion and the bridge check.
- CI on macOS and Linux, Python 3.10 and 3.13.
- README corrected. It documented `log-weight`, `db-search` and `ask`, none of which were ever
  implemented — 0.2.0 announced them and shipped four commands. `db-search` cannot work:
  `SearchFoodnomsDatabaseIntent` presents the food picker and never returns. The other two are
  untested and do not ship until they have been run.
