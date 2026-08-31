# The FoodNoms store

Notes on the database FoodNomsCTL reads, reverse-engineered from the shipping app rather than
documented. Written down so that a future migration is a diff against this page instead of a
rediscovery — which matters, because FoodNoms has already migrated once.

## Finding it

```text
~/Library/Containers/<random-uuid>/Data/Documents/db.db
```

The `<random-uuid>` is the app's sandbox container and differs per machine, so it must be
discovered: walk `~/Library/Containers/*/Data/Documents/db.db` and match each container's
`.com.apple.containermanagerd.metadata.plist` against the bundle id `com.algebraiclabs.foodnoms`.

Two abandoned stores are still on disk and both look convincing:

| Path | Format | Last written |
|---|---|---|
| `~/Library/Group Containers/group.com.algebraiclabs.foodnoms/FoodNoms.sqlite` | Core Data | 2022 |
| `…/group.com.algebraiclabs.foodnoms/com.algebraiclabs.foodnoms/db.db` | GRDB | 2025 |

Reading either returns years-old data with no error. `doctor` reports which store is live and
names the ones it skipped.

The `-wal` and `-shm` sidecars matter: FoodNoms holds the database open, so recent writes live
in the write-ahead log and copying the `.db` alone returns stale rows.

## Tables

### `foodEntryRecord`

One row per logged food, and heavily denormalized — it carries the food's identity *and* its
nutrition, so it is both the log and, deduplicated, the library.

| Column | Meaning |
|---|---|
| `name`, `brandOwner`, `barcode` | The food as logged |
| `foodID` | Stable id, `local:<uuid>` for user-created foods |
| `baseUnit` / `baseAmount` | What `nutrients` is expressed per — 100 g, 15 ml, 1 serving |
| `nutrients` | JSON of macros **per base amount**, not per entry |
| `calories` | Calories for the entry as eaten, already scaled |
| `measure` | JSON `{unit, value}` — the unit chosen and its size |
| `quantity` | How many of that measure |
| `date` | UTC timestamp |
| `day` | Julian day number of the **local** day |
| `tzID` | Olson zone the entry was logged in |
| `mealTypeID` | 1–6, joins `mealTypeRecord` |
| `collectionEditID` | Set when the row is a component of a saved meal or recipe |

### `foodRecord`

The user's own library entries — foods created in the app rather than logged from a database.

### `foodCollectionRecord`

`collectionType` 2 is a saved Meal, 3 is a Recipe. `collectionID` is the raw 16 bytes of a UUID;
rendered and upper-cased it is the identifier FoodNoms' log intents accept, which is what lets a
Shortcut reference a saved meal by name. Members are `foodEntryRecord` rows whose
`collectionEditID` matches.

## Two traps

**Nutrients need scaling, and the obvious scaling is wrong.** `nutrients` is per `baseAmount`,
so the naive `quantity × measure.value / baseAmount` is only correct when `measure.unit` equals
`baseUnit`. Log a tablespoon of a per-100 g food and it is out by an order of magnitude — a
tablespoon of chia seeds reads as 486 kcal. The `calories` column already holds the scaled
figure, so the reliable factor is `calories / nutrients.calories`, which needs no unit
conversion table. Fall back to the direct calculation only for zero-calorie foods, where the
ratio is undefined and the macros are zero anyway.

**Filter days on `day`, never on `date`.** `date` is UTC, so an evening entry in Vancouver lands
on the following UTC date; a date-range window silently takes yesterday evening and drops this
evening. `day` is the app's own local-day key — a Julian day number, `(d - 1970-01-01).days +
2440587.5` — and is what the log screen groups by.
