# Reading Your Library

Every read is fast, offline, and safe to run at any time — the store is copied before it is
opened, so a running FoodNoms never contends on the write-ahead log, and nothing is ever written
back.

Every command takes `--json`.

## `day` — what you ate

```bash
foodnomsctl day
foodnomsctl day 2026-09-03
```

Entries with per-item macros and the day's totals. Components of a saved Meal or Recipe are
excluded: they are parts of a stored item, not separate things eaten.

Days are the app's own local-day key, not a date range over timestamps. Dates are stored in UTC,
so an evening entry in Vancouver lands on the following UTC date — a naive range would take
yesterday evening and drop this evening.

## `catalog` — everything you have ever logged

```bash
foodnomsctl catalog
foodnomsctl catalog --min-count 10
foodnomsctl catalog --since 2026-01-01
```

One row per distinct food, most-logged first, with the count. The most recent logging is taken
as canonical: units, serving sizes and macros drift as brands reformulate, so the latest entry
describes what is actually in your cupboard now.

The count is a good proxy for how much a food matters to you.

## `search` and `resolve` — find one food

```bash
foodnomsctl search "peanut butter"
foodnomsctl resolve "oat milk"
foodnomsctl resolve barcode:0068892324819
foodnomsctl resolve id:foodnoms:usda:2708403
```

`search` returns every match. `resolve` returns exactly one — the most-logged — and exits
non-zero when there is none, which is what you want inside a script.

Ids match in full or on a colon boundary. The old store kept `service` and `serviceID` apart, so
something pinned against it says `usda:2708403` where the live store says `foodnoms:usda:2708403`
— the same food, and worth still finding. A partial segment never matches, so an id is never hit
by accident.

## `meals` and `resolve-meal` — saved Meals

```bash
foodnomsctl meals
foodnomsctl meals smoothie
foodnomsctl resolve-meal "Benny - Yolks Salmon"
```

`meals` lists saved Meals with their items. `resolve-meal` returns the meal's UUID — the same
identifier FoodNoms' log intent takes — so a Shortcut can reference a saved meal by name instead
of by a UUID pasted in by hand.

## `barcodes` — the scan table

```bash
foodnomsctl barcodes
foodnomsctl barcodes --json
```

Every barcode your library knows and the food behind it. Useful because FoodNoms offers no
headless way to resolve a barcode — both of its search intents present a picker — so anything on
a phone needs the answer exported ahead of time.

## `doctor` — is anything wrong

```bash
foodnomsctl doctor
```

Store path, size, entry counts, the abandoned stores it skipped, and whether the bridge Shortcut
is installed. Run it first when something returns nothing. See
[Troubleshooting](Troubleshooting.md).
