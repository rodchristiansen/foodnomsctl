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
- `delete` — remove a logged entry by entry id or by name within a day.
- Entity parameters are bindable after all: an intent takes `{identifier, displayString}`, so
  entity-typed arguments no longer force a picker.
- `--json` before the subcommand is no longer silently un-set by the subparser's own default.
