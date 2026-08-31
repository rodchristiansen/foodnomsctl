# The FoodNoms store

Notes on the Core Data store FoodNomsCTL reads. This is reverse-engineered from the shipping
app, not documentation. It is written down so that when a model migration breaks something, the
fix is a diff against this page rather than a rediscovery.

## Location

```text
~/Library/Group Containers/group.com.algebraiclabs.foodnoms/FoodNoms.sqlite
```

An app group container, so it is TCC-protected: the *responsible* process needs Full Disk
Access. Interactively that is the terminal app; under `launchd` there is no responsible app and
the read is denied — with Python that surfaces as an empty directory listing rather than an
error, because `glob` swallows the `PermissionError`.

The `-wal` and `-shm` sidecars matter. FoodNoms holds the database open, so recent writes live
in the write-ahead log; copying the `.sqlite` alone returns stale data. FoodNomsCTL copies all
three to a temporary directory and opens the copy `mode=ro`.

## Tables

### `ZFOODENTRY`

One row per logged food. This is the important table — it is both the log *and*, deduplicated by
`ZSERVICEID`, the library.

| Column | Meaning |
|---|---|
| `ZNAME` | Display name as logged |
| `ZSERVICE` / `ZSERVICEID` | Which food database the item came from, and its id there |
| `ZBARCODE` | Scanned barcode, when the food was added by scan |
| `ZUNIT` / `ZUNITQUANTITY` | The unit and how much of it one serving is |
| `ZQUANTITY` | How many units this entry logged |
| `ZHOUSEHOLDSERVINGFULLTEXT` | Human serving text, e.g. "2 tbsp" |
| `ZSERVINGSIZE` / `ZSERVINGSIZEUNIT` | Serving size in grams or millilitres |
| `ZCALORIES` `ZPROTEIN` `ZCARBS` `ZFAT` `ZFIBER` `ZSUGARS` `ZSODIUM` | Macros for the entry as logged |
| `ZDATE` | Apple epoch (seconds since 2001-01-01), add `978307200` for Unix |
| `ZMEAL` | Which meal of the day |
| `ZMEALENTITY` | Set when the row belongs to a saved Meal rather than the day's log |
| `ZRECIPEENTITY` | Set when the row belongs to a Recipe |
| `ZMEALSORTINDEX` | Item order within a saved Meal |

`ZMEALENTITY IS NULL AND ZRECIPEENTITY IS NULL` is the filter that separates "actually eaten
today" from "a component of a stored meal or recipe". Without it, day totals double-count.

### `ZMEAL`

Saved Meals.

| Column | Meaning |
|---|---|
| `Z_PK` | Primary key, referenced by `ZFOODENTRY.ZMEALENTITY` |
| `ZNAME` | Meal name as shown in the app |
| `ZMEALID` | The raw 16 bytes of the meal's UUID |

`ZMEALID` is stored as a binary blob, not a string. Rendering it with
`uuid.UUID(bytes=...)` and upper-casing gives exactly the identifier FoodNoms' `LogMealIntent`
expects, which is what makes `resolve-meal` useful: a Shortcut can reference a saved meal by
name and get the UUID at build time.

## Deriving the library

There is no library table. `catalog` partitions `ZFOODENTRY` by `ZSERVICEID`, counts the rows,
and takes the most recent one as canonical:

```sql
SELECT *, COUNT(*) OVER (PARTITION BY ZSERVICEID) cnt,
          ROW_NUMBER() OVER (PARTITION BY ZSERVICEID ORDER BY ZDATE DESC) rn
FROM ZFOODENTRY WHERE ZSERVICEID IS NOT NULL
```

Most-recent-wins is deliberate. Brands reformulate and repackage, so serving sizes and macros
drift over time; the latest entry describes the product currently in the cupboard. The count
that comes with it is a good proxy for how much a food matters — the most-logged protein powder
is almost always the right default when a recipe just says "protein".
