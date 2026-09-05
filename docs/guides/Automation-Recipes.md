# Automation Recipes

Every command takes `--json`, which is the point rather than a convenience: an agent asked "how
much protein did I get yesterday" should answer from the log in milliseconds, not ask you to
open an app and read a number back to it.

These assume `jq`.

## Today's protein against a target

```bash
foodnomsctl day --json | jq '.totals.protein'
```

```bash
foodnomsctl day --json \
  | jq -r '.totals | "\(.protein)g protein · \(.calories | round) kcal"'
```

## The biggest protein sources in a day

```bash
foodnomsctl day 2026-09-03 --json \
  | jq -r '.entries | sort_by(-.protein)[:5][] | "\(.protein)g  \(.name)"'
```

## A week of protein

```bash
for i in $(seq 0 6); do
  d=$(date -v-${i}d +%Y-%m-%d)
  printf "%s  %s\n" "$d" "$(foodnomsctl day "$d" --json | jq '.totals.protein')"
done
```

## Resolve a food to its identifiers

```bash
foodnomsctl resolve "oat milk" --json | jq -r '.[0] | "\(.food_id)  \(.barcode)"'
```

`resolve` exits non-zero when nothing matches, so this is safe in a script with `set -e`.

## Your most-logged foods, as a shopping shortlist

```bash
foodnomsctl catalog --min-count 20 --json \
  | jq -r '.[] | "\(.count)\t\(.name)\t\(.brand // "")"' | column -t -s$'\t'
```

## Everything you logged of one food, ever

```bash
foodnomsctl search "skyr" --json | jq -r '.[] | "\(.count)  \(.name)  \(.last_logged)"'
```

## Export the barcode table for a device

```bash
foodnomsctl barcodes --json > known-foods.json
```

FoodNoms has no headless barcode lookup — both search intents present a picker — so anything
scanning on a phone needs the answer exported ahead of time.

## Log a whole meal, unattended

Queue everything, then drain once. This is much faster than logging one at a time, and the queue
means a locked Mac costs you nothing.

```bash
D="2026-09-03 12:30"
q() { foodnomsctl log "$1" --date "$D" \
        --calories "$2" --protein "$3" --carbs "$4" --fat "$5" --queue-only; }

q "Mediterranean Salad"   560 18 48 34
q "Flatbread & Hummus"    400 12 48 17
q "Steelhead Salmon"      580 53  1 39

foodnomsctl flush
```

All four macros are required — see [Writing to FoodNoms](Writing-To-FoodNoms.md).

## Check whether writes are possible right now

```bash
ioreg -n Root -d1 -a | grep -q CGSSessionScreenIsLocked \
  && echo "locked — writes will queue" \
  || echo "unlocked — writes will land"
```

## Find days you forgot to log

```bash
for i in $(seq 0 30); do
  d=$(date -v-${i}d +%Y-%m-%d)
  n=$(foodnomsctl day "$d" --json | jq '.entries | length')
  [ "$n" -lt 3 ] && echo "$d  only $n entries"
done
```

## Notes for agents

- Reads are safe to call at any frequency; they copy the store and never write.
- Writes are idempotent only in the sense that the queue retires a request already present in
  the store. Do not retry a `log` by re-issuing it — flush the queue instead.
- Never run two drains concurrently. `flush` takes an exclusive lock and a second one exits, but
  the reason that lock exists is that nine queued items once became ninety entries.
