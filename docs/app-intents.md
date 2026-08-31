# Writing FoodNoms actions into a Shortcut

Notes on FoodNoms' App Intents as they are actually accepted, not as the metadata describes
them. Everything here was found by running the intents and reading back what worked; none of
it is documented by the app.

## Where the metadata lives

```text
/Applications/FoodNoms.app/Contents/Resources/Metadata.appintents/extract.actionsdata
```

A JSON document listing every intent, its parameters, whether each is optional, and the cases
of every enum. It is the authority on *what exists* and useless on *what binds* — the two
diverge constantly, and the rest of this page is that gap.

## The intents moved

FoodNoms consolidated logging in 2026. `LogFoodIntent` and `LogDrinkIntent` are **gone**;
both are now `LogIntent` with a `type` enum. An action still pointing at the old identifiers
renders as "Unknown Action" on an updated device and fails with `WFActionErrorDomain error 1`
on macOS. Nothing warns you: a Shortcut written before the update keeps its actions, they
simply stop resolving.

Check the identifier list against the metadata before assuming any intent still exists.

## The shape LogIntent accepts

```json
{
  "AppIntentDescriptor": {
    "TeamIdentifier": "32642VZFU3",
    "BundleIdentifier": "com.algebraiclabs.foodnoms",
    "Name": "Foodnoms",
    "AppIntentIdentifier": "LogIntent"
  },
  "UUID": "…",
  "ShowWhenRun": false,
  "type": "food",
  "foodEntry": {
    "title": {"key": "Organic Maca Powder"},
    "subtitle": {"key": "Organic Maca Powder"},
    "identifier": "{\"value\":{\"foodID\":{\"_0\":{\"serviceID\":\"08503813-…\",\"service\":\"manualEntry\"}}}}"
  }
}
```

`type` is `drink` for a drink, and the food then goes in `drink` rather than `foodEntry`.
`service` is `manualEntry` for a food created in the app and `foodNoms` for one from FoodNoms'
database; the `serviceID` is the store's `foodID` with its `local:` or `foodnoms:` prefix
stripped. The entity identifier is a JSON **document**, not an id — a serialized Swift enum —
and the display name is carried twice, as title and subtitle.

`AppIntentDescriptor` is required. Without it the action does not resolve.

## Omitted means default, and that is the whole trick

`LogIntent` declares `mealType`, `dateTimePreference`, `uncertainty` and `useLastPortion` as
**required**. Supplying them is what breaks it. The Shortcuts editor writes out only the
parameters the user actually set, and an action that names a required parameter the editor
would have omitted fails at run time rather than logging.

So the rule for every FoodNoms intent: write the minimum, and add a parameter only after
seeing the editor write it. Four different `mealType` spellings were tried against this
intent — `"1"`, `"1"` with a `mealTypeID`, `"MealType:1"`, `"breakfast"` — and all four
failed, while omitting it worked first time.

## Quantity needs a measure

`quantity` alone does nothing, as a string or as a number. It counts *measures*, so without a
`foodMeasure` — `drinkMeasure` when `type` is `drink` — the intent quietly ignores it and logs
the portion last used for that food. The three travel together:

```json
"quantity": "32",
"useLastPortion": false,
"drinkMeasure": {
  "title": {"key": "fl oz"},
  "subtitle": {"key": "fl oz"},
  "identifier": "{\"value\":{\"value\":29.603152569971,\"traits\":0,\"descriptionText\":\"fl oz\",\"unit\":\"gram\",\"descriptionQuantity\":1}}"
}
```

The identifier is the store's own `measure` dictionary wrapped in a `value` key — byte for byte
what `foodEntryRecord.measure` holds and what `foodnomsctl resolve` now reports, alongside
`measures`, every portion the food offers. So a measure is never invented, only selected.

Two shapes are worth knowing. A base unit is a measure of size 1 —
`{"traits":0,"unit":"gram","value":1}` — so `quantity` counts grams directly; that form appears
in the store for foods logged by weight. A named portion carries `descriptionText` and the size
of one of them in the base unit, which is how `fl oz` is 29.603152569971 grams of water. A food
whose own portions are only in cups can still be logged in fluid ounces by scaling its base
unit: 29.5735295625 for millilitres.

## `type: drink` is narrower than it looks

`LogIntent`'s `type` enum offers `drink`, and the obvious reading — that anything you drink is
a drink — is wrong. FoodNoms accepts it only for entries its own drink tracking recognises.
Water logs correctly; almond, oat and macadamia milk all fail with "An unknown error occurred.
Please submit a bug report to support@foodnoms.com", and log fine the moment they are sent as
`type: food` instead.

Nothing distinguishes the two cases in the metadata or in the store, so the only way to know is
to log each one and look.

## Prove every food, not the Shortcut

A generated Shortcut can import cleanly, render cleanly, pass validation, and still fail on one
ingredient. Worse, a Shortcut stops at its first failing action, so running the real one finds
only the first bad food — and in a menu-driven Shortcut the failures sit behind prompts that
`shortcuts run` cannot answer.

Test each food in its own single-action Shortcut instead. Thirty-three options took thirty-three
throwaway Shortcuts and about five minutes, and turned "a few errors somewhere" into three named
foods with one shared cause. `bin/foodnoms-verify` in the engine repo automates exactly this.

It logs a real entry per option, so clean the day up afterwards.

## Intents that are not headless

The metadata's `openAppWhenRun: false` does not mean an intent runs without UI.
`SearchFoodnomsDatabaseIntent` and `SearchFoodLibraryIntent` both present FoodNoms' food
picker and block until someone chooses, so `shortcuts run` never returns. There is no
declaration to check — an intent that resolves to entities is liable to do this, and the only
way to find out is to run it once and watch.

This is why a food reference has to be a literal baked in at build time: the obvious
alternative, searching for it at run time, opens a picker.

## How to learn a shape you cannot guess

Guessing entity serializations is a losing game. Read one back instead:

1. Generate a Shortcut containing the action with the unguessable parameters left empty, and
   install it.
2. Open it in the Shortcuts editor, set those parameters by hand, and close the window.
3. Read the saved plist out of the library database.

```sql
SELECT a.ZDATA FROM ZSHORTCUT s
JOIN ZSHORTCUTACTIONS a ON a.Z_PK = s.ZACTIONS
WHERE s.ZNAME = '<name>' AND s.ZTOMBSTONED = 0;
```

`ZDATA` is a binary plist of the action list. The `foodEntry` shape above came from exactly
this round-trip after four guesses failed. The database is at
`~/Library/Shortcuts/Shortcuts.sqlite` — copy it and its `-wal` before reading, and never
write to it, since it is CloudKit-mirrored.

## Installing and deleting

`open` on a `.shortcut` signed `--mode anyone` installs it with no dialog — but only when no
Shortcuts **editor window** is open, which silently swallows the import, and only while the
session is unlocked. Close the editor, unlock the Mac, and verify with `shortcuts list` rather
than assuming.

Installing never replaces: a Shortcut already in the library under that name stays, and you
get a second copy. Deleting is not scriptable — see [issue 001](issues/001-delete-does-not-bind-a-runtime-entity.md).
