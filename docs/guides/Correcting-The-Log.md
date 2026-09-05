# Correcting the Log

## `delete`

```bash
foodnomsctl delete "Cold brew"
foodnomsctl delete "Cold brew" --on 2026-09-03
foodnomsctl delete A34941A0-5D04-4BDE-96B8-7CEF8D04639D --on 2026-09-03
foodnomsctl delete "Cold brew" --on 2026-09-03 --all
```

By name it searches that day's log; by entry id it goes straight there. When a name matches more
than one entry it refuses to guess and lists them, so `--all` is how you say you meant all of
them.

**How it actually works, and why that matters.** `DeleteLoggedFoodIntent` takes an entity array,
and an entity binds from a literal written in when the action is generated or from another
action's output — never from an identifier passed at run time. So the bridge chains
`GetFoodEntriesIntent` into the delete and removes entries **by position**.

That list is not the store's list: the intent omits water and drink entries, so an index
computed from SQL is off by however many it dropped. `delete` therefore asks the intent for its
own list and resolves against that. A name the intent does not return is a stop rather than a
best guess, because deleting is permanent.

One consequence worth knowing: because deletion is positional, the entry removed is not
necessarily the exact one whose id you named — it is an entry of that name at that position.
When you are deduplicating, that is fine. When you mean one specific entry among several with
the same name, check the result.

## `edit`

```bash
foodnomsctl edit "Cold brew" --calories 20
foodnomsctl edit "Cold brew" --scale 0.5
foodnomsctl edit "Cold brew" --to 2026-09-04
```

Corrects an entry's macros, scales what was logged, or moves it to another day.

There is no edit-a-logged-entry intent among FoodNoms' 45, so this is delete plus re-log, and
the re-log is a quick entry: **the barcode and serving measure do not survive.** It tells you
before doing it. When they must survive, use `relog`.

Timestamps are stored in UTC and every intent reads what it is handed as local time, so `edit`
converts before writing back. Without that an entry moved by the UTC offset — seven hours in
Vancouver, enough to slide a late entry onto the next day and change two days' totals.

## `foodnomsctl-relog`

The same correction, keeping the food itself.

FoodNoms' log intent selects its food and portion through entity-typed parameters, and Shortcuts
resolves an entity when the action is *written*, not when it runs. So the only way to keep a
real food is to bake it in as a literal at build time: `relog` generates a one-shot Shortcut per
batch with the foods written in, installs it, deletes the originals and runs it.

Deletion happens only after the replacement Shortcut is installed, because an entry deleted with
no replacement waiting is the one unrecoverable state here.

## Deduplicating

If a drain race or a retry has left several copies of the same entry, delete by id in a loop and
verify by **count** rather than by id — positional deletion means the id you name is not
necessarily the row that goes, so an id-based check reports failure on a delete that worked.

```bash
foodnomsctl day 2026-09-03 --json | jq -r '.entries[].name' | sort | uniq -c | sort -rn | head
```

Then delete until each count is 1, re-reading the day between deletions.
