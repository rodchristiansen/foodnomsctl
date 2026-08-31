# 001 — `delete` accepts the request and does nothing

**Status:** open · **Opened:** 2026-08-30 · **Affects:** `foodnomsctl delete`, `DeleteLoggedFoodIntent`

`foodnomsctl delete <entry-id|name>` reaches `DeleteLoggedFoodIntent` through the bridge
Shortcut, the run exits 0, and the entry is still in the log.

## What is actually wrong

`foodEntries` is an entity array. An entity parameter binds fine from a literal known when the
action is generated — that is how the smoothie generator pins a specific food into a
`LogFoodIntent`. It does not bind from a value arriving at run time. The intent takes the
request, returns nothing, and deletes nothing.

Three identifier forms were tried against the same entry, all rc=0 and all no-ops:

| Form | Example |
|---|---|
| Entry UUID, upper case | `FDA58FE7-748A-40C9-B664-CB261E0ABC88` |
| Entry UUID, lower case | `fda58fe7-748a-40c9-b664-cb261e0abc88` |
| `foodEntryRecord` row id | `19652` |

Nothing in the App Intents metadata distinguishes an entity that can be resolved from a string
from one that cannot, so this is only discoverable by running it.

## Current behaviour

`delete` re-reads the store after the call and exits non-zero if the entry survives, rather than
reporting a success that did not happen. It is marked KNOWN BROKEN in `intents.yaml`.

## The fix

Stop passing an identifier and let Shortcuts produce the entity. In the `delete` branch of the
bridge: `GetFoodEntriesIntent` for the day, a Filter/Match on the entry name inside the
shortcut, then hand the resulting list to `DeleteLoggedFoodIntent` as a variable. Entity arrays
*do* bind from another action's output.

This makes the `delete` branch structurally different from `log` and `create-food`, which are
one action each — the generator in `foodnomsctl-bridge` currently assumes one action per
command and will need to grow multi-action branches.

## Meanwhile

Deleting an entry is a swipe in FoodNoms. The CLI is read-and-append until this is fixed.
