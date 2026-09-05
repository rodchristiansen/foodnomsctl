# The Write Queue

## The problem it solves

Writes are dispatched through Shortcuts, and Shortcuts does not run while a Mac's screen is
locked. `shortcuts run` hangs until it is killed; importing a Shortcut silently does nothing.
Neither reports an error.

That combination is dangerous rather than merely inconvenient. Before the queue existed, nine
backdated meal entries were dispatched at a locked Mac, each reported "submitted", and **none of
them were written**. The failure looked exactly like the known case where the intent writes
successfully and does not return.

If you drive your Mac from a phone, it is locked essentially always — so the write path was
unusable precisely when it was most wanted.

## How it works

Every write is written to a file **before** it is attempted, and removed only once the store
confirms it landed.

```
~/.local/state/foodnomsctl/queue/
  pending/   requests not yet written
  done/      requests confirmed in the store
```

One file per request rather than one append-only log, because requests are written from more
than one process and a directory of small files has no concurrent writer to lose.

A locked screen is detected up front, so `log` returns in about a tenth of a second with the
request safe on disk instead of hanging and losing it:

```
$ foodnomsctl log "Cold brew" --calories 15 --protein 1 --carbs 0 --fat 0
queued — the screen is locked. It will be logged automatically when this Mac is
unlocked, or now from the phone.
```

## Draining

```bash
foodnomsctl flush
```

Drains everything queued. While the screen is locked this costs one `ioreg` call and exits, so
it is cheap to call often.

To drain automatically:

```bash
./install-agent.sh
```

That installs a launchd agent which runs `flush` on an interval and on any change to the queue
directory. There is no launchd trigger for "the screen was unlocked", so it simply retries; the
queue drains within a minute of the Mac becoming usable. Its log is at
`~/Library/Logs/foodnomsctl-flush.log`.

## Why the queue is not in iCloud

Sharing the queue with a phone would be useful, and the obvious home is the Shortcuts iCloud
container alongside the other spool files. It does not work: **a launchd agent does not inherit
the terminal's Full Disk Access**, so an agent draining a queue under `~/Library/Mobile
Documents` dies on `PermissionError` before it reads a single request.

`FOODNOMSCTL_SPOOL` points the queue elsewhere if you want to try it, but the agent needs Full
Disk Access granted explicitly for that to work.

## Two ways this went wrong, and what stops them

Both produced duplicate entries, which is the expensive failure here — a missing meal is cheap
to re-enter, a duplicated one costs a manual delete.

**Two drainers at once.** The agent drains on an interval *and* on directory change, so a drain
started by hand ran beside one started by the agent. Both saw the same pending request, both
dispatched it, and neither had landed when the other checked. Nine queued items became ninety
entries. Draining now takes an exclusive lock and a second drainer leaves rather than waits.
Each request is also claimed by renaming it out of `pending` before it is read, so a crash
mid-write leaves it claimed rather than pending.

**Verification giving up too early.** FoodNoms commits through its own WAL, so a write that had
in fact landed read as missing for a second or two. The request stayed pending, the agent
retried it, and the entry was logged twice ten seconds apart. Verification now settles before
declaring failure.

If you ever do end up with duplicates, [Correcting the Log](Correcting-The-Log.md) covers
removing them.
