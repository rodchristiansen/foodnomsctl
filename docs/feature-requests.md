# Feature requests for FoodNoms

A running list of things that would make FoodNoms automatable, kept here so it accumulates
instead of being rediscovered. Everything below was found by running the intents against a live
library and reading back what happened; none of it is documented by the app, and none of it is a
complaint about the app as a nutrition tracker — FoodNoms is the best one on Apple platforms
precisely because it stays out of the way.

Ordered by how much each would change what is possible, not by how hard it looks.

## The root request

**A write path that is not Shortcuts.** Everything in the next section is a symptom of App
Intents being the only way in. A URL scheme that logs (`foodnoms://log?...`, x-callback-url
style), or a documented local endpoint, would remove every constraint below at once. The
existing `foodnoms://` scheme is navigation-only — `goals/`, `history/goal/`,
`resting-energy/show-data` — so today a script has to generate, sign and install a Shortcut,
and Shortcuts does not run at all while a Mac's screen is locked. That single fact makes
unattended logging impossible on a locked machine no matter how the intents behave.

## Intents that cannot run unattended

### `LogQuickEntryIntent` prompts instead of failing

With `requireMacros: true`, omitting one of calories, protein, carbs or fat does not return an
error — the app puts up its own dialog ("How much total fat?") and waits. On a headless run
nobody can answer it, so `shortcuts run` hangs indefinitely and the automation stalls with no
diagnostic. Fiber, sugars and sodium are correctly optional.

**Ask:** fail with an error when a required macro is absent, or add a parameter that opts out of
prompting. A dialog is the right behaviour when a human ran the Shortcut and the wrong one when
a script did, and the intent cannot currently tell the difference.

### The log intents never return

`LogQuickEntryIntent` completes the write and then does not hand control back: the entry lands,
`shortcuts run` simply never exits. Callers have to poll the database to discover their own
write succeeded and then kill the process.

**Ask:** return after the write, ideally with the created entry.

### `LogWeightIntent` takes a measurement, not a number

`weight` is a measurement type needing a magnitude/unit payload that a generated action cannot
express. The intent is otherwise perfectly headless.

**Ask:** accept a number plus a unit enum, as the macro parameters already do.

### `AskFoodnomsAIIntent` requires an entity-typed parameter

`mealType` is declared required and is entity-typed, and Shortcuts resolves entities through
picker UI — so there is no value a generated action can put there. `logImmediately` is required
too.

**Ask:** make `mealType` optional, defaulting the way the app does when a human logs without
choosing one.

### The search intents present a picker and never return

`SearchFoodnomsDatabaseIntent` and `SearchFoodLibraryIntent` both open the food picker and block
until someone chooses, despite declaring `openAppWhenRun: false`. There is no way to search the
online database from a script.

**Ask:** a variant that returns matches as data rather than resolving one interactively.

## Intents that work but are awkward to use correctly

### `DeleteLoggedFoodIntent` cannot be given an entry id

`foodEntries` is an entity array. An entity binds from a literal written in when the action is
generated, or from another action's output, but never from an identifier arriving at run time —
so deleting a known entry means chaining `GetFoodEntriesIntent` → `Get Item from List` → delete,
and deleting *by position* rather than by identity.

**Ask:** accept an entry identifier directly.

### `GetFoodEntriesIntent` returns a different list than the store holds

It omits water and drink entries, so its ordering is not the log's ordering. Because deletion is
positional, an index computed from the database is wrong by however many entries the intent
dropped — which silently deletes the wrong food.

**Ask:** return every entry, or a parameter to include drinks, or stable ids so position stops
mattering.

### There is no edit-a-logged-entry intent

Correcting a logged entry means deleting it and logging a replacement. A quick-entry replacement
loses the food's barcode and serving measure; keeping them means generating a one-shot Shortcut
with the food baked in as a literal.

**Ask:** an edit intent taking an entry and the fields to change.

## Not FoodNoms' to fix

Recorded so they are not mistaken for app bugs.

- **Shortcuts resolves an entity when the action is written, never when it runs.** This is the
  constraint behind most of the awkwardness above.
- **One unsatisfiable action anywhere fails the whole Shortcut.** Shortcuts validates every
  action before running any of them, so a single unbindable parameter makes a dispatcher return
  "Please choose a value for each parameter in this action" — including for commands that are
  themselves fine. It is why speculative intents cannot simply be added to the bridge and left
  unused.
- **Shortcuts does not run while the screen is locked**, and an import silently no-ops rather
  than erroring.

## Context worth sending along

The database moved from Core Data to GRDB and from the app group container into the app's
sandbox container. Both earlier stores are still on disk, still populated, and still answer
queries — stopping in 2022 and 2025 respectively — so anything reading the store has to discover
the live one rather than hardcode a path. Not a request, but a migration worth knowing others
have tripped over.
