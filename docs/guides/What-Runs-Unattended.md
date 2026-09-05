# What Runs Unattended

The single most important thing to know about this tool: **reads and writes have completely
different requirements.** Reads need nothing but the file. Writes need an unlocked Mac with a
logged-in GUI session.

Everything below was measured against a live 16,495-entry library, not inferred from Apple's
metadata.

## Reads: no GUI, no app, no unlock

These open a snapshot of the database and touch no other process. They work over SSH, with
FoodNoms closed, and while the Mac's screen is locked.

| Command | Typical |
|---|---|
| `doctor` | 0.4s |
| `catalog` | 0.3s |
| `search` · `resolve` | 0.4s |
| `day` · `meals` · `resolve-meal` · `barcodes` | 0.1s |

All take `--json`. This is the surface you can drive from a phone with no caveats at all.

## Writes: an unlocked GUI session

macOS has no command that invokes another app's App Intent directly, so every write goes through
a Shortcut — and **Shortcuts does not run while the screen is locked.** `shortcuts run` hangs
until something kills it, and importing a Shortcut silently does nothing. Neither reports an
error, which is what makes this so easy to misdiagnose.

That is not a limitation `foodnomsctl` can remove; it is what the only supported write path
costs. What it does instead is refuse to lose the write. See [The Write Queue](The-Write-Queue.md).

With the screen unlocked:

| Command | Typical |
|---|---|
| `log` | ~1.3s |
| `goal` | ~3s |
| `delete` | ~2.4s |

With the screen locked, `log` returns in about a tenth of a second having queued the request,
and the drain agent logs it within a minute of the Mac becoming usable.

## The macro rule

`log` **requires calories, protein, carbs and fat.** FoodNoms is configured with
`requireMacros`, and when one is missing it does not fail — it puts up its own dialog ("How much
total fat?") and waits. On a headless run nobody can answer that, so the Shortcut never returns.

`foodnomsctl` refuses up front rather than letting you hang:

```
$ foodnomsctl log "Cold brew" --calories 15 --protein 1
log needs --carbs, --fat: FoodNoms is configured to require calories, protein,
carbs and fat, and it asks for a missing one in a dialog rather than failing —
which never returns on a headless run. Pass 0 if a macro really is zero.
```

Fiber, sugars and sodium are genuinely optional. Pass `0` where a macro really is zero.

## What is deliberately not available

Three FoodNoms intents would be useful and are not wrapped, because none of them can run without
a human:

- **`SearchFoodnomsDatabaseIntent`** and **`SearchFoodLibraryIntent`** present the food picker
  and block until someone chooses, despite declaring `openAppWhenRun: false`. Settled: they
  cannot be wrapped.
- **`AskFoodnomsAIIntent`** declares a required, entity-typed `mealType`, and Shortcuts resolves
  entities through picker UI — there is no value a generated action can put there.
- **`LogWeightIntent`** takes a measurement rather than a number, needing a payload this
  generator does not model.

These are collected as asks in [docs/feature-requests.md](../feature-requests.md).

## Running from a phone

The practical shape: read anything, any time. Write whenever, and let the queue and the drain
agent deal with when the Mac is actually able to. Nothing is lost while the Mac is locked, and
nothing needs re-entering afterwards.
