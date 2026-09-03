# Known issues

No public tracker yet, so open problems live here — one file per issue under `docs/issues/`.

| # | Issue | Status |
|---|---|---|
| [001](docs/issues/001-delete-does-not-bind-a-runtime-entity.md) | `delete` accepts the request and does nothing — an entity parameter will not bind from a run-time value | fixed |
| [002](docs/issues/002-a-write-needs-longer-than-the-timeout.md) | The 25s timeout pkilled the write it was waiting for; a bare `open` installs no Shortcut | fixed |
