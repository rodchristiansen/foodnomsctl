# Contributing

## Running the tests

```bash
python3 -m unittest discover -s tests -v
```

Stdlib `unittest` over a synthetic store built by `tests/fixture.py`, so the suite needs neither
FoodNoms nor your data and runs on Linux. CI covers macOS and Linux on Python 3.10 and 3.13.

## What is worth testing

The arithmetic and the matching — the places where a wrong answer looks like a right one:

- Nutrient scaling by the calorie ratio. A tablespoon of a per-100g food is not a hundred grams.
- The local-day key, anchored on a value read out of a live store rather than a re-derivation of
  the same formula.
- Id matching on a colon boundary, so a partial segment never matches by accident.
- Saved-meal components excluded from a day's totals.
- The bridge name matched exactly, not as a substring.
- The four required macros, since a missing one hangs rather than fails.

Anything touching Shortcuts or the live store is not unit-testable and is verified by hand
against a real library. Say so in the commit when you do.

## The fixture

`tests/fixture.py` reproduces the live schema's *values*, not its declarations: `entryID` and
`collectionID` are TEXT columns holding raw 16-byte UUIDs, and `measure`/`measures`/`nutrients`
are BLOB columns holding JSON text. SQLite's dynamic typing is what makes that work.

If you add a query, add a row that would break it when written naively.

## House rules

- **Never write the FoodNoms store.** It is CloudKit-mirrored; a row inserted behind the app's
  back never syncs. Writes go through App Intents.
- **Never write `~/Library/Shortcuts/Shortcuts.sqlite`.** Same reason, worse blast radius.
- **Snapshot before reading**, with the `-wal` and `-shm`, or you may read a stale checkpoint.
- **Exact equality, never "contains"**, when dispatching on a command name or matching a
  Shortcut. Both mistakes have already shipped once.
- **Verify writes by reading the store back.** The intents return nothing useful and some never
  return at all.
- **Prefer a missing entry to a duplicated one.** A missing meal is cheap to re-enter; a
  duplicate costs a manual delete.

## Adding an intent

The branch set is data in `intents.yaml`; rebuild with `./foodnomsctl-bridge --publish`.

Before adding one, establish that it is headless — the metadata does not say. An intent that
resolves to entities is liable to present a picker and block, and `openAppWhenRun: false` does
not mean otherwise. `docs/app-intents.md` describes how to find out, including how to read back
a parameter shape you cannot guess.

Remember that Shortcuts validates every action before running any of them, so one unsatisfiable
parameter breaks the whole bridge — including commands that are fine.

## Feature requests upstream

Constraints that only FoodNoms can lift are collected in
[docs/feature-requests.md](../feature-requests.md). Add to it rather than working around
something silently.
