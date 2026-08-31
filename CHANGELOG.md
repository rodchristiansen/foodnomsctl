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
