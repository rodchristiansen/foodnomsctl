# foodnomsctl guides

`foodnomsctl` gives FoodNoms a command line on macOS. It reads your library straight out of the
app's own database and writes through the app's own App Intents, so nothing here depends on an
API, an account, or a network.

Start with **[Getting Started](Getting-Started.md)**, then read
**[What Runs Unattended](What-Runs-Unattended.md)** — it is the page that decides how you can
use the tool, because reads and writes have very different requirements.

## The guides

| | |
|---|---|
| [Getting Started](Getting-Started.md) | Install, run `doctor`, ask your first questions |
| [What Runs Unattended](What-Runs-Unattended.md) | Which commands work over SSH, with the screen locked, from a phone |
| [Reading Your Library](Reading-Your-Library.md) | `catalog`, `search`, `resolve`, `day`, `meals`, `barcodes` |
| [Writing to FoodNoms](Writing-To-FoodNoms.md) | `log`, `create-food`, the macro rule, what a write costs |
| [The Write Queue](The-Write-Queue.md) | Why writes are queued, the drain agent, the locked-Mac problem |
| [Correcting the Log](Correcting-The-Log.md) | `delete`, `edit`, and when to reach for `relog` |
| [The Bridge Shortcut](The-Bridge-Shortcut.md) | Generating, signing, installing, and naming it |
| [Troubleshooting](Troubleshooting.md) | Every failure seen so far and what it actually meant |
| [How It Works Inside](How-It-Works-Inside.md) | Store discovery, nutrient scaling, the local-day key |
| [Automation Recipes](Automation-Recipes.md) | Worked `--json` pipelines for scripts and agents |
| [Contributing](Contributing.md) | Tests, the fixture, and the house rules |

## The one-paragraph version

Every entry FoodNoms writes is denormalized — it carries the food's name, brand, barcode, unit,
serving measure and full nutrition — so **the log is the library**. Anything you have ever
scanned or logged is queryable offline, forever, without opening the app. That is what makes a
CLI worth having: automations stop naming foods by identifiers that rot and start resolving
against what is actually in your log.
