# 002 — Shortcuts installs nothing, from any path, silently

**Status:** open · **Opened:** 2026-09-02 · **Affects:** installing any rebuilt bridge

`open` on a `.shortcut` signed `--mode anyone` returns 0 and adds nothing to the library. The
house rule says a signed Shortcut installs with no dialog; on this Mac, as of 2026-09-02,
nothing installs at all.

## What was ruled out

| Hypothesis | Test | Result |
|---|---|---|
| Name collision with the installed bridge | published under `FoodNomsCTL Bridge Test` | still nothing |
| An open Shortcuts editor window swallowing it | quit Shortcuts, relaunched, reopened the file | still nothing |
| A bad signature or truncated archive | header is `AEA1`, 25 KB, same shape as the working 2026-08-30 build | file is fine |
| Quarantine on the downloaded file | `xattr -c`, opened from `~/Downloads` | still nothing |
| Worktree path being unusual | copied to `~/Downloads` and to `iCloud Drive/Focused/shortcuts/` | still nothing |
| `shortcuts list` reading a stale cache | queried `ZSHORTCUT` in `~/Library/Shortcuts/Shortcuts.sqlite` directly | genuinely absent |

`shortcuts run` still works on shortcuts already installed, so the app itself is alive. Nothing
appears in `log show` for the Shortcuts process during an import attempt, which is itself odd.

## Why it matters here

The bridge is the only write path, and it is generated. If a rebuilt bridge cannot be
installed, no change to `intents.yaml` can be tested — including the `date` parameter added in
this branch and the multi-action `delete` branch that issue 001 needs. The CLI's write surface
is frozen at whatever build happens to be installed, currently `v2026.08.30.2200`.

## Not yet tried

Importing on the phone and letting CloudKit carry it back; signing `--mode people-who-know-me`;
a Shortcuts sign-out and back in. All need a human at a screen, which is the thing this repo
exists to avoid.
