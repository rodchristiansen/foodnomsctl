# Troubleshooting

Run `foodnomsctl doctor` first. It is the answer to most of what follows.

## Reads return nothing, or data that stops years ago

FoodNoms has moved its database twice, and both earlier stores are still on disk and still
populated — one stops in 2022, the other in 2025. Point at either and every command answers
confidently with stale data.

`doctor` names the live store and lists the ones it skipped. If it reports a store you did not
expect, that is the finding.

## `doctor` cannot open the store

The container is TCC-protected. The process running `foodnomsctl` needs **Full Disk Access** —
that is your terminal or your agent host, not the CLI, because macOS attributes access to the
responsible process.

A launchd agent does not inherit it, which is why the write queue lives under `~/.local/state`
rather than in iCloud.

## `log` says it needs macros

```
log needs --carbs, --fat: FoodNoms is configured to require calories, protein,
carbs and fat...
```

Working as intended. FoodNoms would otherwise put up a dialog and wait forever. Pass `0` if the
macro really is zero. Fiber, sugars and sodium are optional.

## A write says "queued" and nothing happens

Check the screen is unlocked, then:

```bash
foodnomsctl flush
tail ~/Library/Logs/foodnomsctl-flush.log
ls ~/.local/state/foodnomsctl/queue/pending/
```

A file ending `.claimed` means a drain took it and did not finish — it will not be retried
automatically, which is deliberate: an unfinished write is safer left alone than repeated. Move
it back to a plain `.json` name to retry it, once you are satisfied it did not land.

## `shortcuts run` hangs

Almost always a locked screen. Confirm:

```bash
ioreg -n Root -d1 -a | grep -A1 CGSSessionScreenIsLocked
```

`<true/>` means locked, and no Shortcut will run or import until it is not. Absent means
unlocked.

The other cause is a FoodNoms dialog waiting for input — see the macro rule above. Cancel it,
and the run will end.

## "Couldn't find shortcut"

The bridge is not installed under the name the CLI dispatches to. `doctor` names any near-miss.
Either rebuild it or point at what is there:

```bash
export FOODNOMSCTL_BRIDGE="FoodNomsCTL Bridge 3"
```

Remember that importing never replaces, so a rebuild may have landed beside the old copy under a
numbered name.

## An import did nothing

Three silent causes: a locked screen, an open Shortcuts editor window, or a bare `open` instead
of `open -a Shortcuts`. Close the editor, unlock, and verify by reading the library back rather
than assuming — and copy the `-wal` when you read it, or you may be looking at a stale snapshot.

## Duplicate entries

Two known causes, both fixed, both worth recognising if you see them again: two drainers running
at once, and write verification giving up before FoodNoms had committed. See
[The Write Queue](The-Write-Queue.md) for what stops them and
[Correcting the Log](Correcting-The-Log.md) for cleaning up.

## An entry landed on the wrong day

Dates are stored in UTC; the app buckets by local day. A bare `YYYY-MM-DD` passed to `--date`
logs at noon deliberately, because midnight is the boundary a timezone offset pushes across.
`edit --to` converts before writing back for the same reason.

## Everything worked yesterday and now nothing does

The schema is FoodNoms' internal shape, not a published API, and it has already migrated once
from Core Data. `doctor` fails loudly on schema drift rather than returning quietly wrong
answers — that is what it is for.
