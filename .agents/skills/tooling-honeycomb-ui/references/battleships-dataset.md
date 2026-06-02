# Battleships dataset reference

The four canonical queries from `coilysiren/honeycomb-battleships/docs/reading-honeycomb.md`:

```yaml
misses:
  calculations: [{op: COUNT}]
  breakdowns: [shot.row, shot.col]
  filters:
    - {column: name, op: '=', value: fire}
    - {column: shot.result, op: '=', value: MISS}
  orders: [{op: COUNT, order: descending}]

breakdown:
  calculations: [{op: COUNT}]
  breakdowns: [shot.result]
  filters: [{column: name, op: '=', value: fire}]

score-trend:
  calculations: [{op: AVG, column: game.score}]
  breakdowns: [game.number]
  filters: [{column: name, op: '=', value: game}]
  orders: [{column: game.number, order: ascending}]

opponents:
  calculations: [{op: AVG, column: game.score}]
  breakdowns: [game.opponent]
  filters: [{column: game.opponent, op: exists}]
  orders: [{op: AVG, column: game.score, order: ascending}]
```

Origin and full prose interpretation lives in `honeycomb-battleships/docs/reading-honeycomb.md` (the handoff doc - read it before driving the UI for that dataset).
