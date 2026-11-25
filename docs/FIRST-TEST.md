# First test: does a match stay interesting?

Written on 2026-11-25, before any live match. The two questions come from [DESIGN.md](DESIGN.md). This page fixes how they are measured, so the bar cannot move after the results are in.

## Setup

- 20 rounds, seed 1, alternating attackers. Each shop attacks 10 times and defends 10 times.
- Lemonade spymaster and security chief: `llama3.1:8b`. Pie: `qwen2.5:7b`. Helper in both shops: `gemma3:4b`.
- Each shop takes $45 a day. Three real refund requests arrive daily. Some have no receipt number, and some customers will not pick up the phone.
- Four defenses, at most two a day: `receipt_check` ($2), `once_only` ($1), `small_only` ($0), `callback` ($6).

## Criteria

Rounds 1 to 5 are warm-up. All four must be met to continue as designed.

| Name | Met when |
| --- | --- |
| `attacks_land_late` | At least 2 false notes are paid in rounds 6 to 20 |
| `attacks_vary_late` | For each spymaster, the median similarity of its later notes to its own closest earlier note is under 0.8 (Python's `difflib` ratio) |
| `a_chief_changes_choice` | At least one security chief changes its defenses between two of its own turns, after round 5 |
| `no_single_best_defense` | No one choice of defenses is a best choice in 80% or more of rounds 6 to 20 (ties counted) |

The last two split "the best choice changes" into what a chief did and whether the game is already solved.

## Limits, stated up front

- One match, one seed, three small models. It can show the design is dull. It cannot show the design is good.
- "What if" figures replay the same notes and helper decisions under other defenses. An attacker who saw different defenses might have written something else.
- The attacks are models' own. The world, the real customer notes, the defenses and the referee are written by people.
- Failed model calls are logged and counted. Three in a row end the match.
