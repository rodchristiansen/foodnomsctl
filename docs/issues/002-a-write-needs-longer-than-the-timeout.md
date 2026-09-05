# 002 — the 25s timeout killed the write it was waiting for

**Status:** fixed · **Opened:** 2026-09-02 · **Fixed:** 2026-09-03 · **Affects:** every `call_bridge` write

`foodnomsctl log` reported `log: submitted; the intent did not return. Verify with
foodnomsctl day` and nothing was in the log. The message reads like the known
does-not-return case, where the entry lands and `shortcuts run` simply never exits. It was
the opposite: nothing landed, because the timeout does not merely stop waiting. It pkills
`shortcuts run`, and a write still in flight dies with it.

A cold FoodNoms takes well over 30s to service `LogQuickEntryIntent`. At `timeout=25` every
write was killed at 25s and every one was reported ambiguously. Run by hand with a 65s window,
the same request logged fine. The bound is now 90s.

## The wrong turn this issue originally recorded

This file first claimed Shortcuts would not import anything, from any path, and listed six
ruled-out hypotheses. That was wrong twice over, and both mistakes are worth keeping.

**A bare `open` on a `.shortcut` installs nothing.** It hands the file to LaunchServices,
which returns 0 having done nothing, and `-600` when Shortcuts is not running. `open -a
Shortcuts <file>` installs. The publish step now names the app.

**`shortcuts list` and a plain copy of `Shortcuts.sqlite` both lag.** The library lives in a
WAL-mode database, and copying only the `.sqlite` reads a snapshot from the last checkpoint —
in this case the previous day. Two imports that had actually succeeded looked like failures.
Copying `-wal` and `-shm` alongside it, which `connect()` has always done for the FoodNoms
store, showed them present. Verifying an absence is exactly where a stale read is most
convincing and most wrong.

## Still true, and still awkward

Importing does not replace a same-named Shortcut — it is refused outright, not duplicated —
and the `shortcuts` CLI cannot delete. So a rebuilt bridge published under the canonical name
installs nothing and the old build keeps answering, silently. `--publish` now checks the
library afterwards and says so. `FOODNOMSCTL_BRIDGE` overrides the name the CLI dispatches to,
which is how a new build is tested before it takes over.
