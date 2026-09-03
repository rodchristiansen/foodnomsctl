# 001 — `delete` accepts the request and does nothing

**Status:** fixed · **Opened:** 2026-08-30 · **Fixed:** 2026-09-03 · **Affects:** `foodnomsctl delete`, `DeleteLoggedFoodIntent`

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

## Fixed

Exactly as described above, plus one thing the plan did not anticipate: Shortcuts' filter
actions cannot see an entity's properties, so the entries cannot be matched by name inside the
shortcut. The branch selects by position instead — `GetFoodEntriesIntent` for the day, `Get
Item from List` at an index taken from the request, then `DeleteLoggedFoodIntent`.

The index is not a guess. `GetFoodEntriesIntent` leaves out water and drink entries, so its
order is not the store's, and a position computed from SQL would delete the wrong food. The
new `entries` command returns that same list as text, and the CLI resolves the name against it
before passing a position — so the ordering is observed rather than modelled. A name the intent
does not return is a stop, not a best guess, because deleting is permanent.

Deleting several at once works from the back, since removing one shifts every later position.
