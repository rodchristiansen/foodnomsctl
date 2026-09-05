# How It Works Inside

Useful when something looks wrong and you need to know whether to believe it.

## Finding the store

```
~/Library/Containers/<uuid>/Data/Documents/db.db
```

The directory name is a random UUID that differs per machine, so it cannot be hardcoded.
`foodnomsctl` walks the containers and matches each one's identity plist against FoodNoms'
bundle id.

Two abandoned stores remain on disk and both look plausible — a Core Data store in the app group
container that stops in 2022, and a GRDB copy beside it that stops in 2025. Pointing at either
produces confident, years-stale answers, so `doctor` names them explicitly as skipped.

## Snapshot before read

The store is copied — with its `-wal` and `-shm` sidecars — to a temporary path before every
query. A running FoodNoms never contends on the write-ahead log, reads are consistent, and the
app never notices.

Copying the sidecars is not optional. Without the `-wal` you read from the last checkpoint,
which can be a day behind.

## Why nothing writes the store

It is CloudKit-mirrored — `NSPersistentCloudKitContainer`, with its `ANSCK*` bookkeeping tables
right there beside the data. A row inserted behind the app's back gets no CKRecord, so it never
reaches your phone, and it can leave the export bookkeeping inconsistent with the object graph.

## The log is the library

Every logged entry is denormalized: it carries the food's name, brand, barcode, unit, serving
measure and full nutrition. So the set of things you have ever logged — with counts, with the
units you actually use, with the brand you are actually buying — is recoverable with no API, no
account and no network. That is the observation the whole tool rests on.

## Scaling macros correctly

The `nutrients` JSON is per `baseAmount` of `baseUnit` — 100g, 15ml, one serving — while the
entry records how much was eaten in whatever unit you picked.

Scaling by `quantity × measure.value` only works when that unit *is* the base unit. Log a
tablespoon of a per-100g food and you are out by a factor of ten, which is how a tablespoon of
chia seeds becomes 486 kcal.

The `calories` column already holds the scaled figure, so the ratio between it and the per-base
calories gives the factor for every other macro, with no unit conversion table to get wrong.
Zero-calorie foods give no ratio, so those fall back to the direct calculation, which is exact
when the units agree.

## The local-day key

Entries carry a `day` column — a Julian day number that is the app's own local-day key — and a
`date` in UTC. `day` queries filter on the former.

A date range over the latter would be wrong by the timezone offset: an evening entry in
Vancouver lands on the following UTC date, so the range takes yesterday evening and drops this
evening.

## Ids

Entry and collection ids are stored as the raw 16 bytes of a UUID in columns declared `TEXT`.
SQLite's dynamic typing is why that works, and why anything reproducing the schema has to
reproduce the values rather than the declarations.

The intents want the canonical upper-case string form.

## Entities bind at write time

The constraint behind most of the awkwardness in the write path: **Shortcuts resolves an entity
when the action is written, never when it runs.** An entity binds from a literal baked in at
build time, or from another action's output, and never from a value arriving in a request.

That is why `log` is a quick entry rather than a library reference, why `delete` chains
`GetFoodEntriesIntent` instead of taking an id, and why `relog` generates a one-shot Shortcut
with the foods written in.

## The schema is not a contract

These are GRDB internals, not a published API, and FoodNoms has already migrated once.
`foodnomsctl doctor` is the tripwire: it fails loudly when the shape moves rather than returning
quietly wrong answers.
