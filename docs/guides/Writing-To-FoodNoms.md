# Writing to FoodNoms

Nothing in this tool ever writes the database. The store is CloudKit-mirrored, so a row inserted
behind the app's back gets no CKRecord — it never reaches your phone, and it can leave the
export bookkeeping inconsistent with the object graph. Every write goes through FoodNoms' own
App Intents instead, which is the same split [RemCTL](https://github.com/viticci/remctl) uses
for Reminders.

macOS cannot invoke another app's App Intent directly, so those intents are dispatched by one
generated Shortcut. See [The Bridge Shortcut](The-Bridge-Shortcut.md).

## Before your first write

Two things will bite otherwise.

**`log` requires four macros.** Calories, protein, carbs and fat. FoodNoms is configured with
`requireMacros`, and a missing one produces a *dialog*, not an error — which on a headless run
means the Shortcut hangs forever. `foodnomsctl` refuses up front and names what is missing. Pass
`0` where a macro really is zero. Fiber, sugars and sodium are optional.

**The screen must be unlocked.** Shortcuts does not run against a locked screen. If it is
locked, your write is queued rather than lost — see [The Write Queue](The-Write-Queue.md).

## `log` — log a food with macros

```bash
foodnomsctl log "Cold brew" --calories 15 --protein 1 --carbs 0 --fat 0
foodnomsctl log "Mediterranean Salad" --date "2026-09-03 12:30" \
  --calories 560 --protein 18 --carbs 48 --fat 34
```

`--date` writes to an earlier day. A bare `YYYY-MM-DD` logs at noon, deliberately: FoodNoms
buckets by local day and midnight is the boundary a timezone offset pushes across.

`--fiber`, `--sugars` and `--sodium` are available and optional.

This is a *quick entry* — a name and numbers. It does not reference a food in your library, so
it carries no barcode and no serving measure. That is a constraint of the intent, not a choice:
entity-typed parameters cannot be bound from a value arriving at run time. When you need the
real food, see [Correcting the Log](Correcting-The-Log.md) and `foodnomsctl-relog`.

## `create-food` — add a food to the library

```bash
foodnomsctl create-food "House Granola" --brand "Homemade" \
  --calories 220 --protein 6 --carbs 28 --fat 9
foodnomsctl create-food "Cold Brew" --barcode 0123456789012 --serving-size "250 ml"
```

Creates a library entry rather than logging one. Once it exists, it is scannable and
`resolve`-able like anything else.

## `goal` — today's goal

```bash
foodnomsctl goal
```

A read, but one the local store cannot answer, so it goes through the bridge like a write and
needs the same unlocked session. It is deliberately excluded from the queue: a goal fetched an
hour later is not the same answer, and a stale one is worse than none.

## What a write actually does

1. The request is written to a file in the queue.
2. If the screen is locked, it stops there and returns immediately.
3. Otherwise FoodNoms is launched if it is not running — an intent dispatched at a closed
   FoodNoms fails silently, which is how nine backdated entries were once lost.
4. The Shortcut runs.
5. The store is polled until the entry appears.
6. The request is moved to `done`.

Step 5 matters: the log intent completes the write and then never hands control back, so waiting
for the Shortcut to exit is waiting for something that will not happen. Polling for the entry is
the only honest confirmation, and it is what makes a write take a second rather than a minute
and a half.
