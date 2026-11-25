# Second test: do the coach and the watcher earn their place?

Written on 2026-11-25, after the first test's run finished and before its results were read. The first test is the comparison: the same models and seed with no coach and no watcher.

## What is added

- **Coach** (each shop's own model): before the security chief and the spymaster choose, it reads that role's recent days and offers one suggestion. The agent may ignore it.
- **Watcher** (plain rules): it reads only the shop's own records. A refund the helper tries to pay is flagged when the receipt is not in the book, was already refunded, or is for less than the refund. Two or more flags in a defending day raise the shop's watch level by one. A day with no flags lowers it by one.

| Level | Name | Effect on the next defending day |
| --- | --- | --- |
| 0 | normal | None |
| 1 | warned | Recorded and shown, no effect |
| 2 | limited | Holds any flagged refund |
| 3 | suspended | Holds every refund over $9, and any flagged refund |

It also records, without acting: how often the helper tries to refund, how close each new con is to earlier ones, and when a security chief changes or repeats its choice.

## Measures, fixed now

| Question | Measure |
| --- | --- |
| Do coaches change attacks? | Cons landed and money taken, against the first test |
| Do coaches narrow behavior? | Late median similarity of each spymaster's notes, against the first test |
| Do coaches change defense? | Total profit with the watcher's effect removed by replay, against the first test |
| Is the watcher worth its cost? | Replay the same match at level 0: change in money stolen against change in real customers turned away |
| Does the coach pass rival text along? | Count of suggestions sharing a run of 30 or more characters with a rival's note |

## Predictions

1. The watcher turns away more real customers than it stops cons, because customers with lost receipts raise the same flag a con does.
2. Coaches do not raise money taken by more than $20 over the first test.
3. At least one spymaster's late median similarity is higher with a coach than without.

## Limits

One seed and one match on each side. A difference here is a story, not an effect size. Turning the coach on changes what every later agent sees, so rounds cannot be compared one to one.
